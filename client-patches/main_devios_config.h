#pragma once
// ============================================================================
// DEVIOS Nexus Client v5.0 — Runtime Configuration
// ============================================================================
// This header provides the central configuration singleton for all DEVIOS
// features. Settings persist between app restarts via QSettings (Windows
// Registry: HKCU\Software\DEVIOS\NexusClient).
//
// Included automatically by the DEVIOS Nexus Patcher into relevant source files.
// ============================================================================

#include <QSettings>
#include <QString>
#include <QDateTime>

class DeviosConfig {
public:
    // --- Version info ---
    static const char* Version() { return "5.0.0-alpha"; }
    static const char* ClientName() { return "DEVIOS Nexus"; }

    // --- Ghost Mode: blocks typing indicators and read receipts ---
    static bool GhostModeEnabled() {
        return instance()._ghostMode;
    }
    static void SetGhostMode(bool enabled) {
        instance()._ghostMode = enabled;
        instance().save();
    }

    // --- Anti-Delete: prevents messages from being removed locally ---
    static bool AntiDeleteEnabled() {
        return instance()._antiDelete;
    }
    static void SetAntiDelete(bool enabled) {
        instance()._antiDelete = enabled;
        instance().save();
    }

    // --- Anti-Edit: preserves original message text before edits ---
    static bool AntiEditEnabled() {
        return instance()._antiEdit;
    }
    static void SetAntiEdit(bool enabled) {
        instance()._antiEdit = enabled;
        instance().save();
    }

    // --- Userbot command prefix (default "..") ---
    static QString CommandPrefix() {
        return instance()._commandPrefix;
    }

private:
    bool _ghostMode = true;
    bool _antiDelete = true;
    bool _antiEdit = true;
    QString _commandPrefix = "..";

    DeviosConfig() {
        QSettings s("DEVIOS", "NexusClient");
        _ghostMode     = s.value("ghost_mode", true).toBool();
        _antiDelete    = s.value("anti_delete", true).toBool();
        _antiEdit      = s.value("anti_edit", true).toBool();
        _commandPrefix = s.value("command_prefix", "..").toString();
    }

    void save() {
        QSettings s("DEVIOS", "NexusClient");
        s.setValue("ghost_mode", _ghostMode);
        s.setValue("anti_delete", _antiDelete);
        s.setValue("anti_edit", _antiEdit);
        s.setValue("command_prefix", _commandPrefix);
    }

    static DeviosConfig& instance() {
        static DeviosConfig cfg;
        return cfg;
    }
};
