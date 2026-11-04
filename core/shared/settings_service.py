import os
import json
from typing import Any, Dict, Optional, Union
from core.shared.result import Result, Ok, Err

DEFAULT_SETTINGS: Dict[str, Any] = {
    "font_family": "System Default",
    "font_size": 14,
    "ui_scale": 1.0,
}

DEFAULT_STORAGE_PATH = os.path.expanduser("~/.school_project/settings.json")


class SettingsService:
    """Service responsible for persisting and retrieving user visual settings."""

    def __init__(self, storage_path: Optional[str] = None) -> None:
        self.storage_path = storage_path or DEFAULT_STORAGE_PATH

    def _ensure_storage_dir(self) -> None:
        target_dir = os.path.dirname(self.storage_path)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)

    def _validate_and_build_payload(
        self,
        settings_or_family: Union[Dict[str, Any], str],
        font_size: Optional[Any] = None,
        ui_scale: Optional[Any] = None,
    ) -> Dict[str, Any]:
        if isinstance(settings_or_family, dict):
            payload = self.load_settings()
            payload.update(settings_or_family)
        else:
            payload = {
                "font_family": str(settings_or_family),
                "font_size": font_size if font_size is not None else 14,
                "ui_scale": ui_scale if ui_scale is not None else 1.0,
            }

        try:
            payload["font_size"] = int(payload["font_size"])
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid font_size: {payload.get('font_size')}") from e

        try:
            payload["ui_scale"] = float(payload["ui_scale"])
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid ui_scale: {payload.get('ui_scale')}") from e

        return payload

    def load_settings(self) -> Dict[str, Any]:
        """Load persisted settings from JSON file, falling back to defaults."""
        defaults = dict(DEFAULT_SETTINGS)
        if not os.path.exists(self.storage_path):
            return defaults
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                defaults.update(loaded)
            return defaults
        except Exception:
            return defaults

    def save_settings(
        self,
        settings_or_family: Union[Dict[str, Any], str],
        font_size: Optional[Any] = None,
        ui_scale: Optional[Any] = None,
    ) -> Result[Dict[str, Any], str]:
        """Validate and save settings to disk storage."""
        try:
            payload = self._validate_and_build_payload(settings_or_family, font_size, ui_scale)
            self._ensure_storage_dir()
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            return Ok(payload)
        except Exception as e:
            return Err(f"Failed to persist settings: {e}")

    def reset_settings(self) -> Result[Dict[str, Any], str]:
        """Reset settings to default configuration and persist."""
        return self.save_settings(dict(DEFAULT_SETTINGS))
