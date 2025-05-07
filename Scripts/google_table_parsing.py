import os

import pygsheets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

SERVICE_ACCOUNT_FILE = os.path.join(PROJECT_ROOT, "conferencebothelper-1134fe7c70c9.json")

print(SERVICE_ACCOUNT_FILE)
client = pygsheets.authorize(service_account_file=SERVICE_ACCOUNT_FILE)