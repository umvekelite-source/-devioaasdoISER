#pragma once
// DEVIOS Nexus Client - Runtime Configuration
// This header provides static toggles for Ghost Mode, Anti-Delete, and Anti-Edit.
// Settings persist across the session but reset on app restart.
// Included automatically by the DEVIOS Nexus Patcher into relevant source files.

#include <QSettings>

class DeviosConfig {
public:
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

private:
    bool _ghostMode = true;
    bool _antiDelete = true;
    bool _antiEdit = true;

    DeviosConfig() {
        QSettings s("DEVIOS", "NexusClient");
        _ghostMode  = s.value("ghost_mode", true).toBool();
        _antiDelete = s.value("anti_delete", true).toBool();
        _antiEdit   = s.value("anti_edit", true).toBool();
    }

    void save() {
        QSettings s("DEVIOS", "NexusClient");
        s.setValue("ghost_mode", _ghostMode);
        s.setValue("anti_delete", _antiDelete);
        s.setValue("anti_edit", _antiEdit);
    }

    static DeviosConfig& instance() {
        static DeviosConfig cfg;
        return cfg;
    }
};
