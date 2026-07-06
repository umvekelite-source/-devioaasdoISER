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
    for pattern, replacement in patches:
        # Check if this DEVIOS patch is already present in the file
        check_comment = "DEVIOS"
        if check_comment in content:
            # If the specific replacement block signature is already in the file, skip
            signature = [line for line in replacement.splitlines() if "DEVIOS" in line]
            if signature and signature[0].strip() in content:
                print(f"[!] Patch already applied in: {target_file}")
                continue

        compiled = re.compile(pattern, re.MULTILINE)
        if compiled.search(content):
            content = compiled.sub(replacement, content)
            modified = True
            print(f"[+] Applied patch in: {target_file}")
        else:
            print(f"[-] Original anchor pattern not found in: {target_file}")
            
    if modified:
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(content)
    return modified

patches_db = {
    # 0. Skip Breakpad Compilation in prepare script
    "Telegram/build/prepare/prepare.py": [
        (
            r"^    for\s+stage\s+in\s+stages\s*:",
            "    for stage in stages:\n        if stage['name'] == 'breakpad': continue # DEVIOS: skip breakpad compilation"
        )
    ],
    # 0.1 Disable Crash Reporting in CMake
    "Telegram/CMakeLists.txt": [
        (
            r"project\(Telegram\)",
            "project(Telegram)\nset(DESKTOP_APP_DISABLE_CRASH_REPORTS ON CACHE BOOL \"\" FORCE) # DEVIOS: disable crash reporting"
        )
    ],
    # 1. Local Premium bypass logic inside inline header declaration
    "Telegram/SourceFiles/data/data_user.h": [
        (
            r"bool\s+isPremium\s*\(\s*\)\s*const\s*\{",
            "bool isPremium() const { return true; } // DEVIOS Local Premium\n\tbool old_isPremium() const {"
        )
    ],
    # 2. Sponsored messages AdBlock logic
    "Telegram/SourceFiles/data/components/sponsored_messages.cpp": [
        (
            r"bool\s+SponsoredMessages::canHaveFor\s*\(\s*not_null\s*<\s*History\s*\*\s*>\s*history\s*\)\s*const\s*\{",
            "bool SponsoredMessages::canHaveFor(not_null<History*> history) const {\n\t// DEVIOS AdBlock: sponsored messages are fully disabled\n\treturn false;"
        )
    ],
    # 3. Settings View controls (Privacy UI Section)
    "Telegram/SourceFiles/settings/settings_privacy_security.cpp": [
        (
            r"#include\s+\"settings/settings_privacy_security\.h\"",
            "#include \"settings/settings_privacy_security.h\"\n#include \"main_devios_config.h\" // DEVIOS Settings Config\n#include \"ui/vertical_list.h\"\n#include \"ui/widgets/settings_button.h\"\n#include \"ui/wrap/vertical_layout.h\""
        ),
        (
            r"void\s+PrivacySecurity::setupContent\(\s*not_null<Window::SessionController\*>\s*controller\)\s*\{\s*const\s+auto\s+content\s*=\s*Ui::CreateChild<Ui::VerticalLayout>\(this\);",
            "void PrivacySecurity::setupContent(\n\t\tnot_null<Window::SessionController*> controller) {\n\tconst auto content = Ui::CreateChild<Ui::VerticalLayout>(this);\n\n\t// DEVIOS Settings Box Integration\n\tUi::AddSkip(content);\n\tUi::AddDividerText(content, rpl::single(QString(\"--- DEVIOS NEXUS --- \")));\n\n\tauto ghostBtn = content->add(object_ptr<Ui::SettingsButton>(content, rpl::single(QString(\"Ghost Mode (Invisible & Block Receipts)\")), st::settingsButtonNoIcon));\n\tghostBtn->toggleOn(rpl::single(DeviosConfig::GhostModeEnabled()))->toggledChanges() | rpl::start_with_next([=](bool toggled) { DeviosConfig::SetGhostMode(toggled); }, content->lifetime());\n\n\tauto antiDelBtn = content->add(object_ptr<Ui::SettingsButton>(content, rpl::single(QString(\"Anti-Delete (Retain Deleted Messages)\")), st::settingsButtonNoIcon));\n\tantiDelBtn->toggleOn(rpl::single(DeviosConfig::AntiDeleteEnabled()))->toggledChanges() | rpl::start_with_next([=](bool toggled) { DeviosConfig::SetAntiDelete(toggled); }, content->lifetime());\n\n\tauto antiEditBtn = content->add(object_ptr<Ui::SettingsButton>(content, rpl::single(QString(\"Anti-Edit (Message Modification History)\")), st::settingsButtonNoIcon));\n\tantiEditBtn->toggleOn(rpl::single(DeviosConfig::AntiEditEnabled()))->toggledChanges() | rpl::start_with_next([=](bool toggled) { DeviosConfig::SetAntiEdit(toggled); }, content->lifetime());\n\n\tUi::AddSkip(content);"
        )
    ],
    # 4. Message storage flags and metadata additions
    "Telegram/SourceFiles/history/history_item.h": [
        (
            r"class\s+HistoryItem\s*\{",
            "class HistoryItem {\npublic:\n\tbool isDeletedLocally() const { return _deletedLocally; } // DEVIOS flags\n\tvoid setDeletedLocally(bool val) { _deletedLocally = val; }\n\tvoid storePreEditHistory(const TextWithEntities &text, TimeId date) {\n\t\t_editHistory.push_back({ text, date });\n\t}\n\tstruct EditRecord {\n\t\tTextWithEntities text;\n\t\tTimeId date;\n\t};\n\tconst std::vector<EditRecord> &editHistory() const { return _editHistory; }\nprivate:\n\tbool _deletedLocally = false;\n\tstd::vector<EditRecord> _editHistory;"
        )
    ],
    # 5. Prepend deletion tag visually to deleted message bubble texts
    "Telegram/SourceFiles/history/history_item.cpp": [
        (
            r"TextWithEntities\s+HistoryItem::originalText\s*\(\s*\)\s*const\s*\{",
            "TextWithEntities HistoryItem::originalText() const {\n\t// DEVIOS Anti-Delete label\n\tTextWithEntities result = _text;\n\tif (isDeletedLocally()) {\n\t\tresult.text = \"[DELETED] \" + result.text;\n\t}\n\treturn result;\n}\nTextWithEntities HistoryItem::originalText_unused() const {"
        )
    ],
    # 6. Anti-Delete & Anti-Edit updates hooks inside session processing
    "Telegram/SourceFiles/main/main_session.cpp": [
        (
            r"#include\s+\"main/main_session\.h\"",
            "#include \"main/main_session.h\"\n#include \"main_devios_config.h\" // DEVIOS Config"
        ),
        (
            r"void\s+Session::handleUpdate\s*\(\s*const\s+MTPDupdateDeleteMessages\s+&\s*update\s*\)\s*\{",
            "void Session::handleUpdate(const MTPDupdateDeleteMessages &update) {\n\tif (DeviosConfig::AntiDeleteEnabled()) { // DEVIOS Anti-Delete\n\t\tconst auto &ids = update.vmessages().v;\n\t\tfor (const auto &id : ids) {\n\t\t\tif (const auto message = this->data().message(this->channelId(), id.v)) {\n\t\t\t\tmessage->setDeletedLocally(true);\n\t\t\t\tthis->data().requestViewRepaint(message);\n\t\t\t}\n\t\t}\n\t\treturn;\n\t}"
        ),
        (
            r"void\s+Session::handleUpdate\s*\(\s*const\s+MTPDupdateEditMessage\s+&\s*update\s*\)\s*\{",
            "void Session::handleUpdate(const MTPDupdateEditMessage &update) {\n\tif (DeviosConfig::AntiEditEnabled()) { // DEVIOS Anti-Edit\n\t\tconst auto &msg = update.vmessage();\n\t\tmsg.match([&](const MTPDmessage &data) {\n\t\t\tif (const auto localMsg = this->data().message(this->channelId(), data.vid().v)) {\n\t\t\t\tlocalMsg->storePreEditHistory(localMsg->text(), localMsg->date());\n\t\t\t}\n\t\t});\n\t}"
        )
    ],
    # 7. Ghost Mode sending rules override
    "Telegram/SourceFiles/api/api_sending.cpp": [
        (
            r"#include\s+\"api/api_sending\.h\"",
            "#include \"api/api_sending.h\"\n#include \"main_devios_config.h\" // DEVIOS Config"
        ),
        (
            r"void\s+Sending::sendTyping\s*\(\s*TypingAction\s+action\s*\)\s*\{",
            "void Sending::sendTyping(TypingAction action) {\n\tif (DeviosConfig::GhostModeEnabled()) { // DEVIOS Ghost Mode\n\t\treturn;\n\t}"
        ),
        (
            r"void\s+Sending::readHistory\s*\(\s*MsgId\s+maxId\s*\)\s*\{",
            "void Sending::readHistory(MsgId maxId) {\n\tif (DeviosConfig::GhostModeEnabled()) { // DEVIOS Ghost Mode\n\t\treturn;\n\t}"
        )
    ],
    # 8. Userbot Command processor hook inside input dispatcher
    "Telegram/SourceFiles/history/history_widget.cpp": [
        (
            r"void\s+HistoryWidget::sendTextMessage\s*\(\s*const\s+QString\s+&\s*text\s*\)\s*\{",
            "void HistoryWidget::sendTextMessage(const QString &text) {\n\tif (text.startsWith(\"..\")) { // DEVIOS Command Processor\n\t\tQString cmdLine = text.mid(2).trimmed();\n\t\tQStringList args = cmdLine.split(\" \");\n\t\tQString command = args.isEmpty() ? \"\" : args[0].toLower();\n\t\tif (command == \"ping\") {\n\t\t\tthis->confirmSendText(QString(\"`[DEVIOS // TELEMETRY]`\\n`• Status: NOMINAL`\\n`• System: ONLINE`\"));\n\t\t\treturn;\n\t\t} else if (command == \"shrug\") {\n\t\t\tthis->confirmSendText(QString(\"¯\\\\_(ツ)_/¯\"));\n\t\t\treturn;\n\t\t} else if (command == \"flip\") {\n\t\t\tthis->confirmSendText(QString(\"(╯°□°）╯︵ ┻━┻\"));\n\t\t\treturn;\n\t\t} else if (command == \"hide\") {\n\t\t\tQString rawText = cmdLine.mid(4).trimmed();\n\t\t\tthis->confirmSendText(QString(\"||%1||\").arg(rawText));\n\t\t\treturn;\n\t\t}\n\t}"
        )
    ]
}

if __name__ == "__main__":
    base_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    print(f"[*] Applying patches in root directory: {base_dir}")
    
    # Copy configuration header to the target source folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    src_config = os.path.join(script_dir, "main_devios_config.h")
    dest_config = os.path.join(base_dir, "Telegram/SourceFiles/main_devios_config.h")
    
    try:
        shutil.copyfile(src_config, dest_config)
        print(f"[+] Successfully copied main_devios_config.h to: {dest_config}")
    except Exception as e:
        print(f"[-] Failed to copy configuration file: {e}")
        
    success_count = 0
    for rel_path, patch_list in patches_db.items():
        full_path = os.path.join(base_dir, rel_path)
        if apply_patch(full_path, patch_list):
            success_count += 1
            
    print(f"[+] Patching completed. Applied changes to {success_count} files.")
