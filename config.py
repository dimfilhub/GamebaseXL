"""Persistent user settings (config.json)."""
import json
from pathlib import Path


class Config:
    def __init__(self, file):
        self.file = Path(file)

    def load(self):
        try:
            return json.loads(self.file.read_text())
        except (OSError, ValueError):
            return {}

    def save(self, cfg):
        self.file.write_text(json.dumps(cfg, indent=2))

    def get(self, key, default=None):
        return self.load().get(key, default)

    def set(self, key, value):
        cfg = self.load()
        cfg[key] = value
        self.save(cfg)
