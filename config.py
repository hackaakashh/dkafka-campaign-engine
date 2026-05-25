import os
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

FROM_NAME = os.getenv("FROM_NAME")
FROM_EMAIL = os.getenv("FROM_EMAIL")
REPLY_TO = os.getenv("REPLY_TO")

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

DAY_DURATION_MS = int(os.getenv("DAY_DURATION_MS", 30000))
SEND_THROTTLE_SECONDS = int(os.getenv("SEND_THROTTLE_SECONDS", 10))

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./campaign.db")
