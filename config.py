import os
from dotenv import load_dotenv

load_dotenv()

# ── Kishalay's SMTP config ─────────────────────────────────────────────────
SMTP_HOST     = os.getenv("SMTP_HOST")
SMTP_PORT     = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

FROM_NAME  = os.getenv("FROM_NAME")
FROM_EMAIL = os.getenv("FROM_EMAIL")
REPLY_TO   = os.getenv("REPLY_TO")

BASE_URL             = os.getenv("BASE_URL", "http://localhost:8000")
DAY_DURATION_MS      = int(os.getenv("DAY_DURATION_MS", 30000))
SEND_THROTTLE_SECONDS = int(os.getenv("SEND_THROTTLE_SECONDS", 2))
DATABASE_URL         = os.getenv("DATABASE_URL", "sqlite:///./campaign.db")

# ── Aakash's AI + IMAP config ───────────────────────────────────────────────
ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
IMAP_HOST           = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_USER           = os.getenv("IMAP_USER", "")
IMAP_PASS           = os.getenv("IMAP_PASS", "")
REPLY_POLL_INTERVAL = int(os.getenv("REPLY_POLL_INTERVAL", "15"))

# ── Campaign identity (who is sending) ─────────────────────────────────────
CAMPAIGN_NAME   = os.getenv("CAMPAIGN_NAME",   "Founder video confidence campaign")
CAMPAIGN_GOAL   = os.getenv("CAMPAIGN_GOAL",   "Encourage founders to share honest short videos online")
CAMPAIGN_TONE   = os.getenv("CAMPAIGN_TONE",   "natural, honest, conversational")
CAMPAIGN_AUDIENCE = os.getenv("CAMPAIGN_AUDIENCE", "founders and professionals")
