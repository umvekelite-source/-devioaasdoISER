import os
import sys
import shutil

def apply_patch(target_file, patches):
    """
    Applies custom C++ text replacements to tdesktop files.
    """
    if not os.path.exists(target_file):
        print(f"[-] Target file missing: {target_file}")
        return False
        
    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()

    modified = False
    for orig, replacement in patches:
        if orig in content:
            if replacement in content:
                print(f"[!] Patch already applied in: {target_file}")
                continue
            content = content.replace(orig, replacement)
            modified = True
            print(f"[+] Applied patch in: {target_file}")
        else:
            print(f"[-] Original anchor pattern not found in: {target_file}")
            
    if modified:
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(content)
    return modified

# Complete Patches Database for all DEVIOS features
patches_db = {
    # 1. Local Premium bypass logic
    "Telegram/SourceFiles/data/data_user.cpp": [
        (
            "bool UserData::isPremium() const {\n\treturn _flags & Flag::IsPremium;\n}",
            "bool UserData::isPremium() const {\n\t// DEVIOS Local Premium Override\n\treturn true;\n}"
        )
    ],
    # 2. AdBlock logic
    "Telegram/SourceFiles/data/data_sponsored_messages.cpp": [
        (
            "bool SponsoredMessages::canHaveSponsored(not_null<History*> history) const {",
            "bool SponsoredMessages::canHaveSponsored(not_null<History*> history) const {\n\t// DEVIOS AdBlock: sponsored messages are fully disabled\n\treturn false;"
        )
    ],
    # 3. Pin and folders bypass limits
    "Telegram/SourceFiles/data/data_session.cpp": [
        (
            "int Session::maxPinnedChatsCount() const {\n\treturn isPremium() ? 100 : 5;\n}",
            "int Session::maxPinnedChatsCount() const {\n\t// DEVIOS OpSec Limit Overrides\n\treturn 100;\n}"
        ),
        (
            "int Session::maxFoldersCount() const {\n\treturn isPremium() ? 30 : 10;\n}",
            "int Session::maxFoldersCount() const {\n\t// DEVIOS OpSec Limit Overrides\n\treturn 100;\n}"
        )
    ],
    # 4. Settings View controls (Privacy UI Section)
    "Telegram/SourceFiles/settings/settings_privacy_security.cpp": [
        (
            "#include \"settings/settings_privacy_security.h\"",
            "#include \"settings/settings_privacy_security.h\"\n#include \"main_devios_config.h\""
        ),
        (
            "void PrivacySecurity::setupContent(not_null<Ui::VerticalLayout*> container) {",
            "void PrivacySecurity::setupContent(not_null<Ui::VerticalLayout*> container) {\n\t// DEVIOS Settings Box Integration\n\tcontainer->add(Ui::CreateSkipWidget(container, 10));\n\tcontainer->add(Ui::CreateLabelWidget(container, \"DEVIOS Nexus Settings\", Ui::FlatLabel::InitType::Title));\n\t\n\tcontainer->add(Ui::CreateCheckboxWidget(container, \"Ghost Mode (Invisible & Read Receipts Block)\", DeviosConfig::GhostModeEnabled(), [](bool checked) {\n\t\tDeviosConfig::SetGhostMode(checked);\n\t}));\n\tcontainer->add(Ui::CreateCheckboxWidget(container, \"Anti-Delete (Retain Deleted Messages)\", DeviosConfig::AntiDeleteEnabled(), [](bool checked) {\n\t\tDeviosConfig::SetAntiDelete(checked);\n\t}));\n\tcontainer->add(Ui::CreateCheckboxWidget(container, \"Anti-Edit (Message Modification History)\", DeviosConfig::AntiEditEnabled(), [](bool checked) {\n\t\tDeviosConfig::SetAntiEdit(checked);\n\t}));\n\tcontainer->add(Ui::CreateSkipWidget(container, 15));"
        )
    ],
    # 5. Message storage flags and metadata additions
    "Telegram/SourceFiles/history/history_item.h": [
        (
            "class HistoryItem {",
            "class HistoryItem {\npublic:\n\tbool isDeletedLocally() const { return _deletedLocally; }\n\tvoid setDeletedLocally(bool val) { _deletedLocally = val; }\n\tvoid storePreEditHistory(const TextWithEntities &text, TimeId date) {\n\t\t_editHistory.push_back({ text, date });\n\t}\n\tstruct EditRecord {\n\t\tTextWithEntities text;\n\t\tTimeId date;\n\t};\n\tconst std::vector<EditRecord> &editHistory() const { return _editHistory; }\nprivate:\n\tbool _deletedLocally = false;\n\tstd::vector<EditRecord> _editHistory;"
        )
    ],
    # 6. Prepend deletion tag visually to deleted message bubble texts
    "Telegram/SourceFiles/history/history_item.cpp": [
        (
            "TextWithEntities HistoryItem::originalText() const {",
            "TextWithEntities HistoryItem::originalText() const {\n\tTextWithEntities result = _text;\n\tif (isDeletedLocally()) {\n\t\tresult.text = \"🗑️ \" + result.text;\n\t}\n\treturn result;"
        )
    ],
    # 7. Anti-Delete & Anti-Edit updates hooks inside session processing
    "Telegram/SourceFiles/main/main_session.cpp": [
        (
            "void Session::handleUpdate(const MTPDupdateDeleteMessages &update) {",
            "void Session::handleUpdate(const MTPDupdateDeleteMessages &update) {\n\tif (DeviosConfig::AntiDeleteEnabled()) {\n\t\tconst auto &ids = update.vmessages().v;\n\t\tfor (const auto &id : ids) {\n\t\t\tif (const auto message = this->data().message(this->channelId(), id.v)) {\n\t\t\t\tmessage->setDeletedLocally(true);\n\t\t\t\tthis->data().requestViewRepaint(message);\n\t\t\t}\n\t\t}\n\t\treturn;\n\t}"
        ),
        (
            "void Session::handleUpdate(const MTPDupdateEditMessage &update) {",
            "void Session::handleUpdate(const MTPDupdateEditMessage &update) {\n\tif (DeviosConfig::AntiEditEnabled()) {\n\t\tconst auto &msg = update.vmessage();\n\t\tmsg.match([&](const MTPDmessage &data) {\n\t\t\tif (const auto localMsg = this->data().message(this->channelId(), data.vid().v)) {\n\t\t\t\tlocalMsg->storePreEditHistory(localMsg->text(), localMsg->date());\n\t\t\t}\n\t\t});\n\t}"
        )
    ],
    # 8. Ghost Mode sending rules override (glowing typing/read receipt blocker)
    "Telegram/SourceFiles/api/api_sending.cpp": [
        (
            "void Sending::sendTyping(TypingAction action) {",
            "void Sending::sendTyping(TypingAction action) {\n\tif (DeviosConfig::GhostModeEnabled()) {\n\t\treturn;\n\t}"
        ),
        (
            "void Sending::readHistory(MsgId maxId) {",
            "void Sending::readHistory(MsgId maxId) {\n\tif (DeviosConfig::GhostModeEnabled()) {\n\t\treturn;\n\t}"
        )
    ],
    # 9. Userbot Command processor hook inside input dispatcher
    "Telegram/SourceFiles/history/history_widget.cpp": [
        (
            "void HistoryWidget::sendTextMessage(const QString &text) {",
            "void HistoryWidget::sendTextMessage(const QString &text) {\n\tif (text.startsWith(\"..\")) {\n\t\tQString cmdLine = text.mid(2).trimmed();\n\t\tQStringList args = cmdLine.split(\" \");\n\t\tQString command = args.isEmpty() ? \"\" : args[0].toLower();\n\t\tif (command == \"ping\") {\n\t\t\tauto rtt = this->session().api().getCurrentPingMs();\n\t\t\tthis->confirmSendText(QString(\"`[DEVIOS // TELEMETRY]`\\n`• Status: NOMINAL`\\n`• Link Latency: %1 ms`\").arg(rtt));\n\t\t\treturn;\n\t\t} else if (command == \"shrug\") {\n\t\t\tthis->confirmSendText(QString(\"¯\\\\_(ツ)_/¯\"));\n\t\t\treturn;\n\t\t} else if (command == \"flip\") {\n\t\t\tthis->confirmSendText(QString(\"(╯°□°）╯︵ ┻━┻\"));\n\t\t\treturn;\n\t\t} else if (command == \"hide\") {\n\t\t\tQString rawText = cmdLine.mid(4).trimmed();\n\t\t\tthis->confirmSendText(QString(\"||%1||\").arg(rawText));\n\t\t\treturn;\n\t\t}\n\t}"
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
