# starboard_config.py

import json
import os

CONFIG_FILE = "starboard_config.json"

# Configuración por defecto
default_config = {
    "emoji": "⭐",
    "threshold": 1,
    "channel_id": 123456789012345678  # ← Reemplázalo con un canal válido de tu servidor
}

# Cargar configuración desde el archivo (o usar la predeterminada)
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
else:
    config = default_config.copy()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

# Guardar cambios
def save_config():
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
