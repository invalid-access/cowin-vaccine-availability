import json
import os


DATA_STORE_FILE_NAME = "data_store.json"


def get_send_info():
    if not os.path.exists(DATA_STORE_FILE_NAME):
        return {}

    with open(DATA_STORE_FILE_NAME, "r") as json_file:
        send_info = json.load(json_file)
    return send_info


def set_send_info(send_info):
    with open(DATA_STORE_FILE_NAME, "w") as json_file:
        json.dump(send_info, json_file, indent=3)
