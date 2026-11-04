import json
from typing import Optional
from core.shared.mock_qt import Slot
from core.shared.settings_service import SettingsService


class SettingsAdapterMixin:
    """Reusable Qt Slot mixin providing visual settings persistence for adapters."""

    settings_svc: SettingsService

    @Slot(str, int, float, result=str)
    def saveSettings(self, fontFamily: str, fontSize: int, uiScale: float) -> str:
        """Persist visual settings to disk."""
        res = self.settings_svc.save_settings(fontFamily, fontSize, uiScale)
        return json.dumps({"ok": res.ok, "data": res.data, "error": res.error})

    @Slot(result=str)
    def loadSettings(self) -> str:
        """Load visual settings from disk."""
        data = self.settings_svc.load_settings()
        return json.dumps({"ok": True, "data": data})

    @Slot(result=str)
    def resetSettings(self) -> str:
        """Reset visual settings to defaults on disk."""
        res = self.settings_svc.reset_settings()
        return json.dumps({"ok": res.ok, "data": res.data, "error": res.error})
