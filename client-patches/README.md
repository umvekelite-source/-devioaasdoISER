# DEVIOS Nexus Client

Custom Telegram Desktop client with privacy and productivity enhancements.

## Features

| Feature | Description | Toggle |
|---------|-------------|--------|
| **Ghost Mode** | Blocks typing indicators and read receipts | Settings > Privacy |
| **Anti-Delete** | Prevents deleted messages from disappearing locally | Settings > Privacy |
| **Anti-Edit** | Preserves original text when messages are edited | Settings > Privacy |
| **Local Premium** | Unlocks Premium UI elements (stickers, reactions, limits) | Always ON |
| **AdBlock** | Blocks all sponsored messages in channels | Always ON |
| **Userbot Commands** | Chat commands via `..` prefix | See below |

## Userbot Commands

Type these in any chat — they modify the message text before sending:

| Command | Output |
|---------|--------|
| `..ping` | `[DEVIOS // TELEMETRY] Status: NOMINAL` |
| `..shrug` | `¯\_(ツ)_/¯` |
| `..flip` | `(╯°□°）╯︵ ┻━┻` |
| `..hide <text>` | `\|\|spoiler text\|\|` |

## Build

This project builds automatically via GitHub Actions on every push to `devios-main` or `dev`.

### Manual trigger
Go to **Actions** tab > **DEVIOS Nexus Client Build CI** > **Run workflow**.

### Local test
```bash
# Apply patches to a clean tdesktop source tree:
python client-patches/apply_patches.py path/to/tdesktop

# Dry-run (preview without modifying files):
python client-patches/apply_patches.py path/to/tdesktop --dry-run
```

## Files

| File | Purpose |
|------|---------|
| `client-patches/apply_patches.py` | Regex-based source code patcher (v4.0) |
| `client-patches/main_devios_config.h` | Runtime configuration with QSettings persistence |
| `.github/workflows/build.yml` | GitHub Actions CI/CD pipeline |

## Architecture

The patcher works by applying regex-based find-and-replace operations on the original
Telegram Desktop source code at build time. No fork is maintained — patches are applied
fresh on every CI build against the latest `tdesktop` master.

Settings are persisted via `QSettings` (Windows Registry under `HKCU\Software\DEVIOS\NexusClient`).
