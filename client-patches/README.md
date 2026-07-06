# DEVIOS Nexus Client Patches

This directory contains custom C++ source code patches, configurations, and hooks to modify the Telegram Desktop client for **DEVIOS Nexus Client** (v2.0.0-Alpha).

## Patch Roadmap
1. **Local Premium**: Bypass logic for `SponsoredMessages` (AdBlock), Profile Premium Star, and Chat Limits.
2. **Anti-Delete**: MTProto interceptors for message deletion triggers (`UpdateDeleteMessages`).
3. **Anti-Edit**: History tracking for modified message texts.
4. **Ghost Mode**: Blockers for typing actions and read receipts packets.
5. **Command Processor**: Parser for `.ping`, `.purge`, and `.clog` command prefixes.
