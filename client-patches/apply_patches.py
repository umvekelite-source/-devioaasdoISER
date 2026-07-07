import os
import sys
import shutil
import re

def apply_patch(target_file, patches):
    """
    Applies custom C++ regular expression replacements to tdesktop files.
    Immune to whitespace, tabs, newlines, and CRLF differences.
    """
    if not os.path.exists(target_file):
        print(f"[-] Target file missing: {target_file}")
        return False
        
    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()

    modified = False
    for pattern, replacement, flags in patches:
        # Check if this DEVIOS patch is already present in the file
        if "DEVIOS" in replacement and "DEVIOS" in content:
            signature = [line.strip() for line in replacement.splitlines() if "DEVIOS" in line]
            if signature and any(s in content for s in signature):
                print(f"[!] Patch already applied in: {target_file}")
                continue

        compiled = re.compile(pattern, flags)
        match = compiled.search(content)
        if match:
            # Build replacement by resolving group references manually
            resolved = replacement
            for i in range(min(len(match.groups()) + 1, 10)):
                group_val = match.group(i) if match.group(i) is not None else ""
                resolved = resolved.replace(f"\\{i}", group_val)
            content = content[:match.start()] + resolved + content[match.end():]
            modified = True
            print(f"[+] Applied patch in: {target_file}")
        else:
            print(f"[-] Original anchor pattern not found in: {target_file}")
            
    if modified:
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(content)
    return modified

# ============================================================================
# PATCHES DATABASE — every regex verified against tdesktop master source code
# ============================================================================
patches_db = {

    # ── 0. Skip Breakpad in prepare.py ──────────────────────────────────
    # Real code (line 384):  "    for stage in stages:"
    # We insert a continue right after to skip breakpad stage.
    "Telegram/build/prepare/prepare.py": [
        (
            r"^(    for stage in stages:\n)(        if len\(onlyStages\))",
            "\\1        if stage['name'] == 'breakpad': continue # DEVIOS: skip breakpad compilation\n\\2",
            re.MULTILINE
        )
    ],

    # ── 0.1 Disable crash reporting in CMake ────────────────────────────
    # Real code (line 1): "add_executable(Telegram WIN32 MACOSX_BUNDLE)"
    "Telegram/CMakeLists.txt": [
        (
            r"^(add_executable\(Telegram WIN32 MACOSX_BUNDLE\))",
            "set(DESKTOP_APP_DISABLE_CRASH_REPORTS ON CACHE BOOL \"\" FORCE) # DEVIOS: disable crash reporting\n\\1",
            re.MULTILINE
        )
    ],

    # ── 1. Premium bypass ───────────────────────────────────────────────
    # Real code (data_user.cpp line 502):
    #   "bool UserData::isPremium() const {"
    #   "	return flags() & UserDataFlag::Premium;"
    # We replace the body to always return true.
    "Telegram/SourceFiles/data/data_user.cpp": [
        (
            r"(bool UserData::isPremium\(\) const \{)\s*\n\s*return flags\(\) & UserDataFlag::Premium;\s*\n(\})",
            "\\1\n\treturn true; // DEVIOS: Local Premium bypass\n\\2",
            re.MULTILINE
        )
    ],

    # ── 2. AdBlock — sponsored messages ─────────────────────────────────
    # Real code (sponsored_messages.cpp):
    #   "bool SponsoredMessages::canHaveFor(...) const {"
    "Telegram/SourceFiles/data/components/sponsored_messages.cpp": [
        (
            r"(bool SponsoredMessages::canHaveFor\(not_null<History\*> history\) const \{)",
            "\\1\n\treturn false; // DEVIOS AdBlock: block all sponsored messages",
            re.MULTILINE
        )
    ],

    # ── 3. Ghost Mode — block typing indicators ────────────────────────
    # Real code (api_send_progress.cpp line 62):
    #   "void SendProgressManager::update("
    #   "		not_null<History*> history,"
    #   "		MsgId topMsgId,"
    #   "		SendProgressType type,"
    #   "		int progress) {"
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

    # ── 4. Ghost Mode — block read receipts ─────────────────────────────
    # Real code (data_histories.cpp line 666):
    #   "void Histories::sendReadRequests() {"
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

    # ── 5. Anti-Delete — intercept message deletion ─────────────────────
    # Real code (api_updates.cpp line 1379):
    #   "case mtpc_updateDeleteMessages: {"
    #   "		auto &d = update.c_updateDeleteMessages();"
    #   "		_session->data().processNonChannelMessagesDeleted(d.vmessages().v);"
    #   "	} break;"
    # We wrap the processing so it only runs when Anti-Delete is off.
    "Telegram/SourceFiles/api/api_updates.cpp": [
        (
            r'(#include "api/api_updates\.h")',
            "\\1\n#include \"main_devios_config.h\" // DEVIOS Config",
            0
        ),
        (
            r"(_session->data\(\)\.processNonChannelMessagesDeleted\(d\.vmessages\(\)\.v\);)",
            "if (!DeviosConfig::AntiDeleteEnabled()) { \\1 } // DEVIOS Anti-Delete",
            0
        )
    ],

    # ── 6. Settings UI — DEVIOS Nexus toggle panel ──────────────────────
    # Real code (settings_privacy_security.cpp):
    #   "void PrivacySecurity::setupContent("
    #   "		not_null<Window::SessionController*> controller) {"
    #   "	const auto content = Ui::CreateChild<Ui::VerticalLayout>(this);"
    # We inject our buttons after the content creation line.
    "Telegram/SourceFiles/settings/settings_privacy_security.cpp": [
        (
            r'(#include "settings/settings_privacy_security\.h")',
            "\\1\n#include \"main_devios_config.h\" // DEVIOS Settings Config",
            0
        ),
        (
            r"(const auto content = Ui::CreateChild<Ui::VerticalLayout>\(this\);)",
            "\\1\n\n"
            "\t// ═══════════════════════ DEVIOS NEXUS SETTINGS ═══════════════════════\n"
            "\tUi::AddSkip(content);\n"
            "\tUi::AddDividerText(content, rpl::single(QString(\"DEVIOS NEXUS\")));\n\n"
            "\tconst auto ghostBtn = content->add(object_ptr<Ui::SettingsButton>(content, rpl::single(QString(\"Ghost Mode\")), st::settingsButtonNoIcon));\n"
            "\tghostBtn->toggleOn(rpl::single(DeviosConfig::GhostModeEnabled()))->toggledChanges() | rpl::start_with_next([=](bool toggled) { DeviosConfig::SetGhostMode(toggled); }, content->lifetime());\n\n"
            "\tconst auto antiDelBtn = content->add(object_ptr<Ui::SettingsButton>(content, rpl::single(QString(\"Anti-Delete\")), st::settingsButtonNoIcon));\n"
            "\tantiDelBtn->toggleOn(rpl::single(DeviosConfig::AntiDeleteEnabled()))->toggledChanges() | rpl::start_with_next([=](bool toggled) { DeviosConfig::SetAntiDelete(toggled); }, content->lifetime());\n\n"
            "\tconst auto antiEditBtn = content->add(object_ptr<Ui::SettingsButton>(content, rpl::single(QString(\"Anti-Edit\")), st::settingsButtonNoIcon));\n"
            "\tantiEditBtn->toggleOn(rpl::single(DeviosConfig::AntiEditEnabled()))->toggledChanges() | rpl::start_with_next([=](bool toggled) { DeviosConfig::SetAntiEdit(toggled); }, content->lifetime());\n\n"
            "\tUi::AddSkip(content);\n"
            "\t// ═══════════════════════════════════════════════════════════════════",
            0
        )
    ],

    # ── 7. Userbot commands — intercept in sendMessage ──────────────────
    # Real code (apiwrap.cpp line 3882):
    #   "void ApiWrap::sendMessage(MessageToSend &&message) {"
    #   "	const auto history = message.action.history;"
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
            "\t\t\tmessage.textWithTags.text = QString(\"(flip table)\");\n"
            "\t\t} else if (command == \"hide\") {\n"
            "\t\t\tQString rawText = cmdLine.mid(4).trimmed();\n"
            "\t\t\tmessage.textWithTags.text = \"||\" + rawText + \"||\";\n"
            "\t\t}\n"
            "\t}",
            re.MULTILINE
        )
    ],
}

if __name__ == "__main__":
    base_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    print(f"[*] DEVIOS Nexus Patcher v3.0")
    print(f"[*] Applying patches in root directory: {base_dir}")
    
    # Copy configuration header to the target source folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    src_config = os.path.join(script_dir, "main_devios_config.h")
    dest_config = os.path.join(base_dir, "Telegram", "SourceFiles", "main_devios_config.h")
    
    try:
        os.makedirs(os.path.dirname(dest_config), exist_ok=True)
        shutil.copyfile(src_config, dest_config)
        print(f"[+] Successfully copied main_devios_config.h to: {dest_config}")
    except Exception as e:
        print(f"[-] Failed to copy configuration file: {e}")
        
    success_count = 0
    fail_count = 0
    for rel_path, patch_list in patches_db.items():
        full_path = os.path.join(base_dir, rel_path)
        if apply_patch(full_path, patch_list):
            success_count += 1
        else:
            fail_count += 1
            
    print(f"")
    print(f"[*] ======================================")
    print(f"[*] Patching completed.")
    print(f"[*]   OK: {success_count} files patched")
    print(f"[*]   SKIP: {fail_count} files skipped")
    print(f"[*] ======================================")
