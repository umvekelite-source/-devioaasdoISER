# DEVIOS Nexus Client

> Custom Telegram Desktop client with privacy, productivity, and userbot enhancements.

## Features

| Feature | Description | Control |
|---------|-------------|---------|
| **Ghost Mode** | Blocks typing indicators and read receipts (blue ticks) | Toggle in Settings |
| **Anti-Delete** | Deleted messages stay visible — works in personal chats AND channels | Toggle in Settings |
| **Anti-Edit** | Blocks message edit propagation — you see the original text | Toggle in Settings |
| **Local Premium** | Unlocks Premium UI: stickers, reactions, chat limits, profile star | Always ON |
| **AdBlock** | Removes all sponsored messages from channels | Always ON |
| **Userbot** | Built-in chat commands via `..` prefix | See below |
| **Persistent Settings** | All toggles survive app restart (Windows Registry) | Automatic |

## Userbot Commands

Type in any chat — the text is processed before sending:

| Command | Output |
|---------|--------|
| `..ping` | System status + version info |
| `..shrug` | ¯\\\_(ツ)\_/¯ |
| `..flip` | (╯°□°）╯︵ ┻━┻ |
| `..hide <text>` | \|\|spoiler text\|\| |
| `..time` | Current date and time |
| `..me <action>` | \* action text (IRC-style) |
| `..help` | List all available commands |

## Building

### Automatic (GitHub Actions)

Push to `devios-main` or `dev` branch → build runs automatically.

- **Result**: `DEVIOS_Nexus.exe` in Actions → Artifacts
- **Release**: Push tag `v1.0.0` → auto-creates GitHub Release with changelog

### Manual trigger

Actions tab → **DEVIOS Nexus Client Build CI** → **Run workflow**

### Local testing

```bash
# Apply patches to a clean tdesktop source:
python client-patches/apply_patches.py /path/to/tdesktop

# Preview without modifying files:
python client-patches/apply_patches.py /path/to/tdesktop --dry-run
```

## Project Structure

```
.github/workflows/build.yml     CI/CD pipeline with disk cleanup
client-patches/
  apply_patches.py               Regex patcher v5.0 (16 patches, dynamic file resolution)
  main_devios_config.h           Singleton config with QSettings persistence
  README.md                      This file
.gitignore                       Excludes build artifacts
README.md                       Root repo README with badges
```

## How It Works

```
Push to GitHub → Actions triggers → Downloads tdesktop → 
apply_patches.py injects 16 modifications → Compiles → .exe
```

No fork maintained. Patches applied fresh on every build.

Settings stored in Windows Registry: `HKCU\Software\DEVIOS\NexusClient`

## Patched Files (16 modifications across 8 files)

| File | Patches | Purpose |
|------|---------|---------|
| `prepare.py` | 1 | Skip Breakpad compilation |
| `CMakeLists.txt` | 1 | Disable crash reporting |
| `data_user.cpp` | 1 | Premium bypass |
| `sponsored_messages.cpp` | 1 | AdBlock |
| `api_send_progress.cpp` | 2 | Ghost Mode (typing) |
| `data_histories.cpp` | 2 | Ghost Mode (read receipts) |
| `api_updates.cpp` | 4 | Anti-Delete (DM + channels) + Anti-Edit |
| `settings_privacy_security.cpp` | 2 | Settings UI toggles |
| `apiwrap.cpp` | 2 | Userbot command processor |
