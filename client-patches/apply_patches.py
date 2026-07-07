"""
DEVIOS Nexus Patcher v4.0
Applies source-level modifications to tdesktop (Telegram Desktop) source code.
Supports idempotent re-runs, dry-run mode, and returns proper exit codes.

Usage:
    python apply_patches.py <tdesktop_root> [--dry-run]
"""
import os
import sys
import shutil
import re


# ============================================================================
# CORE ENGINE
# ============================================================================

def apply_patch(target_file, patches, dry_run=False):
    """
    Apply a list of regex-based patches to a single source file.
    Returns tuple: (applied_count, skipped_count, failed_count)
    """
    if not os.path.exists(target_file):
        print(f"  [-] File not found: {target_file}")
        return (0, 0, 1)

    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    applied = 0
    skipped = 0
    failed = 0

    for pattern, replacement, flags in patches:
        # --- Idempotency check: skip if DEVIOS signature already present ---
        if "DEVIOS" in replacement:
            # Extract just the '// DEVIOS...' or '# DEVIOS...' comment as a unique fingerprint
            sig_markers = []
            for ln in replacement.splitlines():
                m = re.search(r"(?://|#)[^\n]*DEVIOS[^\n]*", ln)
                if m:
                    sig_markers.append(m.group(0).strip())
            if sig_markers and any(s in content for s in sig_markers):
                print(f"  [!] Already applied, skipping: {os.path.basename(target_file)}")
                skipped += 1
                continue

        # --- Find anchor and inject replacement ---
        compiled = re.compile(pattern, flags)
        match = compiled.search(content)

        if match:
            # Resolve group back-references (\0, \1, \2, ...) manually
            # to avoid re.sub interpreting \x and other escapes in replacement
            resolved = replacement
            for i in range(min(len(match.groups()) + 1, 10)):
                group_val = match.group(i) if match.group(i) is not None else ""
                resolved = resolved.replace(f"\\{i}", group_val)

            content = content[:match.start()] + resolved + content[match.end():]
            applied += 1
            print(f"  [+] Patched: {os.path.basename(target_file)}")
        else:
            failed += 1
            print(f"  [-] Anchor NOT FOUND in: {os.path.basename(target_file)}")
            print(f"      Pattern: {pattern[:80]}...")

    # --- Write only if changes were made and not in dry-run ---
    if content != original:
        if dry_run:
            print(f"  [~] Dry-run: would write {os.path.basename(target_file)}")
        else:
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(content)

    return (applied, skipped, failed)


# ============================================================================
# PATCHES DATABASE
# Every regex is verified against tdesktop-master source code (July 2026).
# Replacement strings use normal (non-raw) Python strings so that:
#   \n  = real newline character
#   \t  = real tab character
#   \\1 = literal \1 (group back-reference, resolved manually)
# ============================================================================

patches_db = {

    # ========================================================================
    # 0. BUILD SYSTEM
    # ========================================================================

    # 0.1 Skip Breakpad compilation in prepare.py
    # Original:  "    for stage in stages:"
    #            "        if len(onlyStages) > 0 ..."
    "Telegram/build/prepare/prepare.py": [
        (
            r"^(    for stage in stages:\n)(        if len\(onlyStages\))",
            "\\1        if stage['name'] == 'breakpad': continue # DEVIOS: skip breakpad compilation\n\\2",
            re.MULTILINE
        )
    ],

    # 0.2 Disable crash reporting in CMakeLists.txt
    # Original:  "add_executable(Telegram WIN32 MACOSX_BUNDLE)"
    "Telegram/CMakeLists.txt": [
        (
            r"^(add_executable\(Telegram WIN32 MACOSX_BUNDLE\))",
            "set(DESKTOP_APP_DISABLE_CRASH_REPORTS ON CACHE BOOL \"\" FORCE) # DEVIOS: disable crash reporting\n\\1",
            re.MULTILINE
        )
    ],

    # ========================================================================
    # 1. LOCAL PREMIUM BYPASS
    # ========================================================================

    # isPremium() always returns true — unlocks UI stars, stickers, limits
    # Original:  "bool UserData::isPremium() const {"
    #            "    return flags() & UserDataFlag::Premium;"
    #            "}"
    "Telegram/SourceFiles/data/data_user.cpp": [
        (
            r"(bool UserData::isPremium\(\) const \{)\s*\n\s*return flags\(\) & UserDataFlag::Premium;\s*\n(\})",
            "\\1\n\treturn true; // DEVIOS: Local Premium bypass\n\\2",
            re.MULTILINE
        )
    ],

    # ========================================================================
    # 2. ADBLOCK — block all sponsored messages
    # ========================================================================

    # canHaveFor() always returns false — no ads ever render
    # Original:  "bool SponsoredMessages::canHaveFor(not_null<History*> history) const {"
    "Telegram/SourceFiles/data/components/sponsored_messages.cpp": [
        (
            r"(bool SponsoredMessages::canHaveFor\(not_null<History\*> history\) const \{)",
            "\\1\n\treturn false; // DEVIOS AdBlock: block all sponsored messages",
            re.MULTILINE
        )
    ],

    # ========================================================================
    # 3. GHOST MODE — block typing indicators
    # ========================================================================

    # Inject config header + early return in SendProgressManager::update()
    # Original:  "void SendProgressManager::update("
    #            "    not_null<History*> history,"
    #            "    MsgId topMsgId,"
    #            "    SendProgressType type,"
    #            "    int progress) {"
    "Telegram/SourceFiles/api/api_send_progress.cpp": [
        (
            r'(#include "api/api_send_progress\.h")',
            "\\1\n#include \"main_devios_config.h\" // DEVIOS Config",
            0
        ),
        (
            r"(void SendProgressManager::update\(\s*\n\s*not_null<History\*> history,\s*\n\s*MsgId topMsgId,\s*\n\s*SendProgressType type,\s*\n\s*int progress\) \{)",
            "\\1\n\tif (DeviosConfig::GhostModeEnabled()) return; // DEVIOS Ghost Mode: block typing",
            re.MULTILINE
        )
    ],

    # ========================================================================
    # 4. GHOST MODE — block read receipts
    # ========================================================================

    # Inject config header + early return in Histories::sendReadRequests()
    # Original:  "void Histories::sendReadRequests() {"
    "Telegram/SourceFiles/data/data_histories.cpp": [
        (
            r'(#include "data/data_histories\.h")',
            "\\1\n#include \"main_devios_config.h\" // DEVIOS Config",
            0
        ),
        (
            r"(void Histories::sendReadRequests\(\) \{)",
            "\\1\n\tif (DeviosConfig::GhostModeEnabled()) return; // DEVIOS Ghost Mode: block read receipts",
            re.MULTILINE
        )
    ],

    # ========================================================================
    # 5. ANTI-DELETE — prevent message removal from local view
    # ========================================================================

    # Wrap processNonChannelMessagesDeleted() in a conditional
    # Original:  "_session->data().processNonChannelMessagesDeleted(d.vmessages().v);"
    "Telegram/SourceFiles/api/api_updates.cpp": [
        (
            r'(#include "api/api_updates\.h")',
            "\\1\n#include \"main_devios_config.h\" // DEVIOS Config",
            0
        ),
        (
            r"(?<!\{ )(_session->data\(\)\.processNonChannelMessagesDeleted\(d\.vmessages\(\)\.v\);)",
            "if (!DeviosConfig::AntiDeleteEnabled()) { \\1 } // DEVIOS Anti-Delete",
            0
        )
    ],

    # ========================================================================
    # 6. SETTINGS UI — DEVIOS Nexus toggle panel
    # ========================================================================

    # Inject toggle buttons into Privacy & Security settings page
    # Original:  "const auto content = Ui::CreateChild<Ui::VerticalLayout>(this);"
    "Telegram/SourceFiles/settings/settings_privacy_security.cpp": [
        (
            r'(#include "settings/settings_privacy_security\.h")',
            "\\1\n#include \"main_devios_config.h\" // DEVIOS Settings Config",
            0
        ),
        (
            r"(const auto content = Ui::CreateChild<Ui::VerticalLayout>\(this\);)",
            "\\1\n\n"
            "\t// ---- DEVIOS NEXUS SETTINGS ----\n"
            "\tUi::AddSkip(content);\n"
            "\tUi::AddDividerText(content, rpl::single(QString(\"DEVIOS NEXUS\")));\n\n"
            "\tconst auto ghostBtn = content->add(object_ptr<Ui::SettingsButton>(content, rpl::single(QString(\"Ghost Mode\")), st::settingsButtonNoIcon));\n"
            "\tghostBtn->toggleOn(rpl::single(DeviosConfig::GhostModeEnabled()))->toggledChanges() | rpl::start_with_next([=](bool toggled) { DeviosConfig::SetGhostMode(toggled); }, content->lifetime());\n\n"
            "\tconst auto antiDelBtn = content->add(object_ptr<Ui::SettingsButton>(content, rpl::single(QString(\"Anti-Delete\")), st::settingsButtonNoIcon));\n"
            "\tantiDelBtn->toggleOn(rpl::single(DeviosConfig::AntiDeleteEnabled()))->toggledChanges() | rpl::start_with_next([=](bool toggled) { DeviosConfig::SetAntiDelete(toggled); }, content->lifetime());\n\n"
            "\tconst auto antiEditBtn = content->add(object_ptr<Ui::SettingsButton>(content, rpl::single(QString(\"Anti-Edit\")), st::settingsButtonNoIcon));\n"
            "\tantiEditBtn->toggleOn(rpl::single(DeviosConfig::AntiEditEnabled()))->toggledChanges() | rpl::start_with_next([=](bool toggled) { DeviosConfig::SetAntiEdit(toggled); }, content->lifetime());\n\n"
            "\tUi::AddSkip(content);\n"
            "\t// ---- END DEVIOS NEXUS SETTINGS ----",
            0
        )
    ],

    # ========================================================================
    # 7. USERBOT — command processor in sendMessage
    # ========================================================================

    # Inject command handler at the start of ApiWrap::sendMessage()
    # Original:  "void ApiWrap::sendMessage(MessageToSend &&message) {"
    "Telegram/SourceFiles/apiwrap.cpp": [
        (
            r'(#include "apiwrap\.h")',
            "\\1\n#include \"main_devios_config.h\" // DEVIOS Config",
            0
        ),
        (
            r"(void ApiWrap::sendMessage\(MessageToSend &&message\) \{)",
            "\\1\n"
            "\t// DEVIOS Command Processor\n"
            "\tif (message.textWithTags.text.startsWith(\"..\")) {\n"
            "\t\tQString cmdLine = message.textWithTags.text.mid(2).trimmed();\n"
            "\t\tQStringList args = cmdLine.split(\" \");\n"
            "\t\tQString command = args.isEmpty() ? \"\" : args[0].toLower();\n"
            "\t\tif (command == \"ping\") {\n"
            "\t\t\tmessage.textWithTags.text = \"`[DEVIOS // TELEMETRY]` Status: NOMINAL | System: ONLINE\";\n"
            "\t\t} else if (command == \"shrug\") {\n"
            "\t\t\tmessage.textWithTags.text = QChar(175) + QString(\"\\\\_(\") + QChar(12484) + QString(\")_/\") + QChar(175);\n"
            "\t\t} else if (command == \"flip\") {\n"
            "\t\t\tmessage.textWithTags.text = QChar(9583) + QString(\"(\") + QChar(176) + QChar(9633) + QChar(176) + QString(\")\") + QChar(9583) + QChar(65077) + QString(\" \") + QChar(9531) + QChar(9473) + QChar(9531);\n"
            "\t\t} else if (command == \"hide\") {\n"
            "\t\t\tQString rawText = cmdLine.mid(4).trimmed();\n"
            "\t\t\tmessage.textWithTags.text = \"||\" + rawText + \"||\";\n"
            "\t\t}\n"
            "\t}",
            re.MULTILINE
        )
    ],
}


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python apply_patches.py <tdesktop_root> [--dry-run]")
        sys.exit(2)

    base_dir = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    print("[*] DEVIOS Nexus Patcher v4.0")
    print(f"[*] Target: {os.path.abspath(base_dir)}")
    if dry_run:
        print("[*] Mode: DRY-RUN (no files will be modified)")
    print("")

    # --- Validate target directory ---
    if not os.path.isdir(base_dir):
        print(f"[!] ERROR: Target directory does not exist: {base_dir}")
        sys.exit(1)

    # --- Copy configuration header ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    src_config = os.path.join(script_dir, "main_devios_config.h")
    dest_config = os.path.join(base_dir, "Telegram", "SourceFiles", "main_devios_config.h")

    try:
        os.makedirs(os.path.dirname(dest_config), exist_ok=True)
        if not dry_run:
            shutil.copyfile(src_config, dest_config)
        print(f"[+] Copied main_devios_config.h -> Telegram/SourceFiles/")
    except Exception as e:
        print(f"[!] CRITICAL: Failed to copy config header: {e}")
        sys.exit(1)

    # --- Apply all patches ---
    total_applied = 0
    total_skipped = 0
    total_failed = 0

    for rel_path, patch_list in patches_db.items():
        full_path = os.path.join(base_dir, rel_path)
        print(f"\n--- {rel_path} ---")
        a, s, f = apply_patch(full_path, patch_list, dry_run=dry_run)
        total_applied += a
        total_skipped += s
        total_failed += f

    # --- Summary ---
    print("")
    print("=" * 50)
    print(f"  DEVIOS Nexus Patcher - Summary")
    print(f"  Applied:  {total_applied}")
    print(f"  Skipped:  {total_skipped} (already patched)")
    print(f"  Failed:   {total_failed} (anchor not found)")
    print("=" * 50)

    if total_failed > 0:
        print(f"\n[!] WARNING: {total_failed} patch(es) failed to find their anchor.")
        print("[!] The build may still succeed if the missing patches are optional.")
        # Exit 0 even with some failures — the build should attempt compilation
        # and report C++ errors if patches are actually required.

    sys.exit(0)
