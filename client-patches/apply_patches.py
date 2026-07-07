"""
DEVIOS Nexus Patcher v5.0 (ULTRA MAX EDITION)
Applies source-level modifications to tdesktop (Telegram Desktop) source code.

Features:
  - Idempotent: safe to run multiple times on the same source tree
  - Dynamic file resolution: finds files even if they move between directories
  - Forgiving regex anchors: tolerant to whitespace differences
  - Dry-run mode: preview changes without writing files

Usage:
    python apply_patches.py <tdesktop_root> [--dry-run]
"""
import os
import sys
import shutil
import re
import time


# ============================================================================
# CORE ENGINE
# ============================================================================

def find_file_dynamically(base_dir, target_rel_path):
    """
    If a file is not found at the exact relative path, do a recursive search
    in the Telegram/ directory tree to find it. This handles cases where
    tdesktop developers move files between folders.
    """
    exact_path = os.path.join(base_dir, target_rel_path)
    if os.path.exists(exact_path):
        return exact_path

    filename = os.path.basename(target_rel_path)
    
    # Search Telegram/ tree first (covers both SourceFiles and build dirs)
    search_root = os.path.join(base_dir, "Telegram")
    if os.path.exists(search_root):
        for root, dirs, files in os.walk(search_root):
            if filename in files:
                found_path = os.path.join(root, filename)
                print(f"  [i] Resolved: {filename} -> {os.path.relpath(found_path, base_dir)}")
                return found_path

    return exact_path  # Return original to trigger the "not found" message


def apply_patch(base_dir, target_rel_path, patches, dry_run=False):
    """
    Apply a list of regex-based patches to a single source file.
    Returns tuple: (applied_count, skipped_count, failed_count)
    """
    target_file = find_file_dynamically(base_dir, target_rel_path)

    if not os.path.exists(target_file):
        print(f"  [-] File not found: {target_file}")
        return (0, 0, 1)

    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    applied = 0
    skipped = 0
    failed = 0

    for patch_entry in patches:
        # Support 3-tuple (pattern, replacement, flags) or 4-tuple (..., apply_all)
        if len(patch_entry) == 4:
            pattern, replacement, flags, apply_all = patch_entry
        else:
            pattern, replacement, flags = patch_entry
            apply_all = False

        # --- Idempotency check: skip if DEVIOS signature already present ---
        if "DEVIOS" in replacement:
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
        
        if apply_all:
            # Apply to ALL matches (iterate from end to preserve positions)
            matches = list(compiled.finditer(content))
            if matches:
                for match in reversed(matches):
                    resolved = replacement
                    for i in range(min(len(match.groups()) + 1, 10)):
                        group_val = match.group(i) if match.group(i) is not None else ""
                        resolved = resolved.replace(f"\\{i}", group_val)
                    content = content[:match.start()] + resolved + content[match.end():]
                applied += len(matches)
                print(f"  [+] Patched: {os.path.basename(target_file)} ({len(matches)} occurrences)")
            else:
                failed += 1
                print(f"  [-] Anchor NOT FOUND in: {os.path.basename(target_file)}")
                print(f"      Pattern: {pattern[:80]}...")
        else:
            # Single match (default)
            match = compiled.search(content)
            if match:
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
# ============================================================================

patches_db = {

    # ========================================================================
    # 0. BUILD SYSTEM
    # ========================================================================

    # 0.1 Skip Breakpad compilation in prepare.py
    "Telegram/build/prepare/prepare.py": [
        (
            r"^(    for stage in stages:\n)(        if len\(onlyStages\))",
            "\\1        if stage['name'] == 'breakpad': continue # DEVIOS: skip breakpad compilation\n\\2",
            re.MULTILINE
        )
    ],

    # 0.2 Disable crash reporting in CMakeLists.txt
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
    # 5. ANTI-DELETE + ANTI-EDIT — api_updates.cpp
    # ========================================================================
    "Telegram/SourceFiles/api/api_updates.cpp": [
        (
            r'(#include "api/api_updates\.h")',
            "\\1\n#include \"main_devios_config.h\" // DEVIOS Config",
            0
        ),
        # 5a. Anti-Delete: block personal/group message deletion
        (
            r"(?<!\{ )(_session->data\(\)\.processNonChannelMessagesDeleted\(d\.vmessages\(\)\.v\);)",
            "if (!DeviosConfig::AntiDeleteEnabled()) { \\1 } // DEVIOS Anti-Delete",
            0
        ),
        # 5b. Anti-Delete: block CHANNEL message deletion
        (
            r"(?<!\{ )(_session->data\(\)\.processMessagesDeleted\(\s*\n\s*peerFromChannel\(d\.vchannel_id\(\)\.v\),\s*\n\s*d\.vmessages\(\)\.v\);)",
            "if (!DeviosConfig::AntiDeleteEnabled()) {\n\t\t\\1\n\t\t} // DEVIOS Anti-Delete Channels",
            re.MULTILINE
        ),
        # 5c. Anti-Edit: block ALL message edit propagation (personal + channel)
        (
            r"(?<!\{ )(_session->data\(\)\.updateEditedMessage\(d\.vmessage\(\)\);)",
            "if (!DeviosConfig::AntiEditEnabled()) { \\1 } // DEVIOS Anti-Edit",
            0,
            True  # apply_all: catch both personal and channel edit handlers
        )
    ],

    # ========================================================================
    # 6. SETTINGS UI — DEVIOS Nexus toggle panel
    # ========================================================================
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
            "\tUi::AddDividerText(content, rpl::single(QString(\"DEVIOS NEXUS v\" + QString(DeviosConfig::Version()))));\n\n"
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
    # 7. USERBOT — Ultra Max Command Processor
    # ========================================================================
    "Telegram/SourceFiles/apiwrap.cpp": [
        (
            r'(#include "apiwrap\.h")',
            "\\1\n#include \"main_devios_config.h\" // DEVIOS Config\n#include <QDateTime> // DEVIOS Userbot",
            0
        ),
        (
            # Ultra forgiving regex — tolerates different whitespace styles
            r"(void\s+ApiWrap::sendMessage\(MessageToSend\s*&&\s*message\)\s*\{)",
            "\\1\n"
            "\t// DEVIOS Command Processor v5.0\n"
            "\t{\n"
            "\t\tQString txt = message.textWithTags.text;\n"
            "\t\tQString prefix = DeviosConfig::CommandPrefix();\n"
            "\t\tif (txt.startsWith(prefix)) {\n"
            "\t\t\tQString cmdLine = txt.mid(prefix.length()).trimmed();\n"
            "\t\t\tQStringList args = cmdLine.split(\" \");\n"
            "\t\t\tQString cmd = args.isEmpty() ? \"\" : args[0].toLower();\n"
            "\t\t\tif (cmd == \"ping\") {\n"
            "\t\t\t\tmessage.textWithTags.text = \"`[DEVIOS // TELEMETRY]`\\nStatus: NOMINAL\\nSystem: ONLINE\\nVersion: \" + QString(DeviosConfig::Version());\n"
            "\t\t\t} else if (cmd == \"shrug\") {\n"
            "\t\t\t\tmessage.textWithTags.text = QChar(175) + QString(\"\\\\_(\") + QChar(12484) + QString(\")_/\") + QChar(175);\n"
            "\t\t\t} else if (cmd == \"flip\") {\n"
            "\t\t\t\tmessage.textWithTags.text = QChar(9583) + QString(\"(\") + QChar(176) + QChar(9633) + QChar(176) + QString(\")\") + QChar(9583) + QChar(65077) + QString(\" \") + QChar(9531) + QChar(9473) + QChar(9531);\n"
            "\t\t\t} else if (cmd == \"hide\") {\n"
            "\t\t\t\tQString rawText = cmdLine.mid(4).trimmed();\n"
            "\t\t\t\tmessage.textWithTags.text = \"||\" + rawText + \"||\";\n"
            "\t\t\t} else if (cmd == \"time\") {\n"
            "\t\t\t\tmessage.textWithTags.text = \"`[DEVIOS // TIME]` \" + QDateTime::currentDateTime().toString(\"yyyy-MM-dd HH:mm:ss\");\n"
            "\t\t\t} else if (cmd == \"me\") {\n"
            "\t\t\t\tQString rawText = cmdLine.mid(2).trimmed();\n"
            "\t\t\t\tmessage.textWithTags.text = \"* \" + rawText;\n"
            "\t\t\t} else if (cmd == \"help\") {\n"
            "\t\t\t\tmessage.textWithTags.text = QString(\"DEVIOS NEXUS v%1 Commands:\\n\"\n"
            "\t\t\t\t\t\"..ping - System status\\n\"\n"
            "\t\t\t\t\t\"..shrug - Shrug emoticon\\n\"\n"
            "\t\t\t\t\t\"..flip - Table flip\\n\"\n"
            "\t\t\t\t\t\"..hide <text> - Spoiler text\\n\"\n"
            "\t\t\t\t\t\"..time - Current time\\n\"\n"
            "\t\t\t\t\t\"..me <action> - Action text\\n\"\n"
            "\t\t\t\t\t\"..help - This message\").arg(DeviosConfig::Version());\n"
            "\t\t\t}\n"
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

    start_time = time.time()

    print("=" * 50)
    print("  DEVIOS Nexus Patcher v5.0 (ULTRA MAX EDITION)")
    print("=" * 50)
    print(f"  Target: {os.path.abspath(base_dir)}")
    if dry_run:
        print("  Mode:   DRY-RUN (no files will be modified)")
    print("")

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
        print(f"\n--- {rel_path} ---")
        a, s, f = apply_patch(base_dir, rel_path, patch_list, dry_run=dry_run)
        total_applied += a
        total_skipped += s
        total_failed += f

    # --- Summary ---
    elapsed = time.time() - start_time
    print("")
    print("=" * 50)
    print(f"  DEVIOS Nexus Patcher - Summary")
    print(f"  Applied:  {total_applied}")
    print(f"  Skipped:  {total_skipped} (already patched)")
    print(f"  Failed:   {total_failed} (anchor not found)")
    print(f"  Time:     {elapsed:.2f}s")
    print("=" * 50)

    if total_failed > 0:
        print(f"\n[!] WARNING: {total_failed} patch(es) failed to find their anchor.")
        print("[!] The build may still succeed if the missing patches are optional.")

    sys.exit(0)
