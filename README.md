
# SMTP-First Email Campaign Engine

Built by **Kishalay** (SMTP engine) + **Aakash** (AI scheduler + state machine).

---

## Setup (5 minutes)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Fill in your API key in .env
# Open .env and set ANTHROPIC_API_KEY=sk-ant-...

# 3. Create database tables
python init_db.py

# 4. Start the server
uvicorn app:app --reload --port 8000
```

---

## Enroll a subscriber

```bash
curl -X POST http://localhost:8000/enroll \
  -H "Content-Type: application/json" \
  -d '{"name": "Aakash Test", "email": "your-real-inbox@gmail.com"}'
```

The campaign starts automatically. Every 30 seconds = 1 campaign day.

---

## Run the demo console (second terminal)

While the campaign is running:

```bash
python -m aakash.demo_console
```

Commands:
```
open   your@email.com                            → simulate open
click  your@email.com                            → simulate click
reply  your@email.com  "This sounds interesting" → positive reply → AI responds
reply  your@email.com  "Please stop emailing me" → negative reply → farewell → DO_NOT_CONTACT
bounce your@email.com                            → bounce → all sends stop
status                                           → show all subscriber states
events                                           → show event log
```

---

## Check subscriber status

```
GET http://localhost:8000/status
```

---

## State Machine

```
ACTIVE (enrolled)
  │ Day 1
  ▼
EMAIL_SENT_D1 ── Day 2, no open ──► RESENT_D2
  │                                      │
  └─── open event ──────────────────────►┘
                                         │
                                    OPENED
                                         │ next tick
                                    MOFU_SENT
                                         │ click
                                    CLICKED
                                         │ next tick
                                    BOFU_SENT
                                         │
           ┌─────────────────────────────┤
           │ positive reply              │ negative reply
           ▼                             ▼
   REPLIED_POSITIVE             REPLIED_NEGATIVE
           │ next tick                   │ next tick
     AI reply sent               farewell sent (once)
           │                             │
       ENGAGED                   DO_NOT_CONTACT ✋
           │ Day 7
         SUNSET ✋

   BOUNCED ✋  (any time)
   UNSUBSCRIBED ✋  (any time)
```

---

## Architecture

| File | Owner | What it does |
|------|-------|-------------|
| `app.py` | Kishalay+Aakash | FastAPI app, tracking endpoints |
| `mailer.py` | Kishalay+Aakash | SMTP send + `send_email_direct()` for AI content |
| `models.py` | Kishalay+Aakash | SQLAlchemy models |
| `aakash/scheduler.py` | **Aakash** | Campaign brain — ticks every 30s |
| `aakash/ai_agent.py` | **Aakash** | Claude API: generate emails, classify replies |
| `aakash/reply_detector.py` | **Aakash** | IMAP polling + test harness |
| `aakash/state_machine.py` | **Aakash** | State constants |
| `aakash/demo_console.py` | **Aakash** | Interactive demo terminal |

---

## What's working
- SMTP send through Gmail
- Open / click / unsubscribe / bounce tracking
- 7-day accelerated campaign (30s per day)
- AI-generated emails for each funnel stage (TOFU/MOFU/BOFU/SUNSET)
- Reply classification (positive/negative/neutral)
- AI warm reply referencing what subscriber actually said
- One graceful farewell on negative reply → permanent DO_NOT_CONTACT
- State transitions driven by behaviour, not fixed schedule

## What would be added in production
- SPF / DKIM / DMARC on a real sending domain
- Webhook-based bounce handling (Postmark/SendGrid callbacks)
- Proper IMAP reply threading (In-Reply-To header matching)
- Multiple subscribers / bulk enroll CSV
- Dashboard UI
