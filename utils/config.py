# utils/config.py
import os

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

ACCESS_KEY = os.getenv("CLEVER_KEY_ID")
SECRET_KEY = os.getenv("CLEVER_KEY_SECRET")
ENDPOINT_URL = "https://cellar-c2.services.clever-cloud.com"
REGION_NAME = "par"
BUCKET_NAME = "extract"
