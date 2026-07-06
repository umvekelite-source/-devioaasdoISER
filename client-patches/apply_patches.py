import os
import sys

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

# Patch definitions
patches_db = {
    "Telegram/SourceFiles/data/data_user.cpp": [
        (
            "bool UserData::isPremium() const {\n\treturn _flags & Flag::IsPremium;\n}",
            "bool UserData::isPremium() const {\n\t// DEVIOS Local Premium Override\n\treturn true;\n}"
        )
    ],
    "Telegram/SourceFiles/data/data_sponsored_messages.cpp": [
        (
            "bool SponsoredMessages::canHaveSponsored(not_null<History*> history) const {",
            "bool SponsoredMessages::canHaveSponsored(not_null<History*> history) const {\n\t// DEVIOS AdBlock: sponsored messages are fully disabled\n\treturn false;"
        )
    ],
    "Telegram/SourceFiles/data/data_session.cpp": [
        (
            "int Session::maxPinnedChatsCount() const {\n\treturn isPremium() ? 100 : 5;\n}",
            "int Session::maxPinnedChatsCount() const {\n\t// DEVIOS OpSec Limit Overrides\n\treturn 100;\n}"
        ),
        (
            "int Session::maxFoldersCount() const {\n\treturn isPremium() ? 30 : 10;\n}",
            "int Session::maxFoldersCount() const {\n\t// DEVIOS OpSec Limit Overrides\n\treturn 100;\n}"
        )
    ]
}

if __name__ == "__main__":
    base_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    print(f"[*] Applying patches in root directory: {base_dir}")
    
    success_count = 0
    for rel_path, patch_list in patches_db.items():
        full_path = os.path.join(base_dir, rel_path)
        if apply_patch(full_path, patch_list):
            success_count += 1
            
    print(f"[+] Patching completed. Applied changes to {success_count} files.")
