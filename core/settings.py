import os
import json
from config import APP_DATA_DIR

SETTINGS_FILE = os.path.join(APP_DATA_DIR, "settings.json")

class Settings:
    def __init__(self):
        self.refinement_enabled = False
        self.refinement_format = "Prompt"
        self.refinement_context = ""
        self.load()

    def load(self):
        if os.path.exists(SETTINGS_FILE):
             try:
                 with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                     data = json.load(f)
                     self.refinement_enabled = data.get("refinement_enabled", False)
                     self.refinement_format = data.get("refinement_format", "Prompt")
                     self.refinement_context = data.get("refinement_context", "")
             except Exception:
                 pass

    def save(self):
        data = {
            "refinement_enabled": self.refinement_enabled,
            "refinement_format": self.refinement_format,
            "refinement_context": self.refinement_context
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

# Global settings instance
app_settings = Settings()
