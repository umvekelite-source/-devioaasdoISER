#pragma once

class DeviosConfig {
public:
    static bool GhostModeEnabled() { return _ghostMode; }
    static void SetGhostMode(bool enabled) { _ghostMode = enabled; }
    
    static bool AntiDeleteEnabled() { return _antiDelete; }
    static void SetAntiDelete(bool enabled) { _antiDelete = enabled; }
    
    static bool AntiEditEnabled() { return _antiEdit; }
    static void SetAntiEdit(bool enabled) { _antiEdit = enabled; }
    
private:
    inline static bool _ghostMode = true;
    inline static bool _antiDelete = true;
    inline static bool _antiEdit = true;
};
