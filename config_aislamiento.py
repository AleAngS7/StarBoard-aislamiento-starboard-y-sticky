import json
import os

CONFIG_FILE = "aislamiento.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_log_channel_id(guild_id):
    config = load_config()
    return config.get(str(guild_id), {}).get("timeout_log_channel")

def set_log_channel_id(guild_id, channel_id):
    config = load_config()
    gid = str(guild_id)
    if gid not in config:
        config[gid] = {}
    config[gid]["timeout_log_channel"] = channel_id
    save_config(config)
