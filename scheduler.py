"""
Campaign Scheduler — the real brain.
Replaces Kishalay's basic scheduler_loop.

Every tick = 1 campaign day (default 30 seconds).
Reads fresh subscriber state from DB on every tick.
State + event history → decides exactly what to send next.
"""

import time
import json
from uuid import uuid4

from config import DAY_DURATION_MS, SEND_THROTTLE_SECONDS
from database import SessionLocal
from models import Subscriber, Event
from mailer import send_email_direct

from aakash.state_machine import (
    ACTIVE, EMAIL_SENT_D1, RESENT_D2, OPENED, MOFU_SENT,
    CLICKED, BOFU_SENT, REPLIED_POSITIVE, REPLIED_NEGATIVE,
    ENGAGED, TERMINAL_STATES, SUNSET, DO_NOT_CONTACT
)
from aakash.ai_agent import AIAgent
from aakash.reply_detector import ReplyDetector

DAY_SECS = DAY_DURATION_MS / 1000


def scheduler_loop():
    """Entry point — called as a daemon thread from app.py lifespan."""
    print(f"\n[SCHEDULER] Starting. 1 day = {DAY_SECS}s | Full 7-day run ≈ {7*DAY_SECS:.0f}s\n")

    ai       = AIAgent()
    detector = ReplyDetector(ai)
    detector.start()

    for day in range(1, 8):
        print(f"\n{'='*55}")
        print(f"[SCHEDULER]  ⏰  DAY {day}  TICK")
        print(f"{'='*55}")

        db = SessionLocal()
        try:
            # Advance day counter for all active subscribers
            db.query(Subscriber).filter(
                ~Subscriber.state.in_(list(TERMINAL_STATES))
            ).update({"current_day": day}, synchronize_session=False)
            db.commit()

            subs = db.query(Subscriber).filter(
                ~Subscriber.state.in_(list(TERMINAL_STATES))
            ).all()

            if not subs:
                print("[SCHEDULER] No active subscribers — done.")
                break

            for sub in subs:
                try:
                    _tick(sub, day, ai, db)
                    time.sleep(SEND_THROTTLE_SECONDS)   # anti-spam throttle
                except Exception as e:
                    print(f"[SCHEDULER ERROR] {sub.email}: {e}")

            db.commit()
        finally:
            db.close()

        if day < 7:
            print(f"\n[SCHEDULER] Sleeping {DAY_SECS}s until Day {day+1}…")
            time.sleep(DAY_SECS)

    print("\n[SCHEDULER] 7-day campaign run complete.")
    detector.stop()


def _tick(sub: Subscriber, day: int, ai: AIAgent, db):
    """Process one subscriber on one day tick."""

    # Always re-read state in case tracking endpoints changed it
    db.refresh(sub)
    state = sub.state
    email = sub.email

    print(f"[TICK] {email} | Day {day} | State: {state}")

    if state in TERMINAL_STATES:
        print(f"[TICK] {email} terminal ({state}) — skip")
        return

    # ── Day 1: Enroll → send first email ───────────────────────────────
    if state == ACTIVE:
        subject, html, text = ai.generate_email(sub.name, stage="TOFU", day=1)
        _send(sub, subject, html, text, db)
        sub.state = EMAIL_SENT_D1
        _log(sub, "SENT", db, extra={"subject": subject, "day": 1})
        print(f"[DAY 1] ✉  {email} | '{subject}'")

    # ── Day 2+: No open → resend with new subject ───────────────────────
    elif state == EMAIL_SENT_D1 and day >= 2:
        subject, html, text = ai.generate_email(
            sub.name, stage="RESEND", day=day,
            extra_hint="Different subject. More personal. They did not open the first email."
        )
        _send(sub, subject, html, text, db)
        sub.state = RESENT_D2
        _log(sub, "SENT", db, extra={"subject": subject, "day": day, "resend": True})
        print(f"[DAY 2 RESEND] ✉  {email} | '{subject}'")

    # ── Opened → MOFU follow-up ─────────────────────────────────────────
    elif state == OPENED:
        subject, html, text = ai.generate_email(sub.name, stage="MOFU", day=day)
        _send(sub, subject, html, text, db)
        sub.state = MOFU_SENT
        _log(sub, "SENT", db, extra={"subject": subject, "day": day, "stage": "MOFU"})
        print(f"[MOFU] ✉  {email} | '{subject}'")

    # ── Clicked → BOFU stronger follow-up ──────────────────────────────
    elif state == CLICKED:
        subject, html, text = ai.generate_email(sub.name, stage="BOFU", day=day)
        _send(sub, subject, html, text, db)
        sub.state = BOFU_SENT
        _log(sub, "SENT", db, extra={"subject": subject, "day": day, "stage": "BOFU"})
        print(f"[BOFU] ✉  {email} | '{subject}'")

    # ── Positive reply → AI drafts warm human reply ─────────────────────
    elif state == REPLIED_POSITIVE:
        reply_text = _get_last_reply_text(sub.email, db)
        if not reply_text:
            print(f"[AI REPLY] No reply text found for {email}, skipping this tick")
            return

        history = json.loads(sub.conversation_history or "[]")
        html, text = ai.generate_reply(sub.name, reply_text, history)

        # Use "Re: [last subject]" as subject
        last_subject = _get_last_subject(sub.email, db) or "our conversation"
        re_subject = last_subject if last_subject.startswith("Re:") else f"Re: {last_subject}"

        _send(sub, re_subject, html, text, db)

        # Update conversation history
        history.append({"role": "subscriber", "content": reply_text})
        history.append({"role": "campaign",   "content": text})
        sub.conversation_history = json.dumps(history)
        sub.state = ENGAGED
        _log(sub, "AI_REPLY_SENT", db, extra={"preview": text[:100]})
        print(f"[AI REPLY] ✉  {email} → ENGAGED (conversation active)")

    # ── Negative reply → one farewell, then DO_NOT_CONTACT ─────────────
    elif state == REPLIED_NEGATIVE:
        # Only send farewell once
        if _has_event(sub.email, "FAREWELL_SENT", db):
            sub.state = DO_NOT_CONTACT
            print(f"[FAREWELL] {email} already received farewell → DO_NOT_CONTACT")
            return

        reply_text = _get_last_reply_text(sub.email, db) or "not interested"
        farewell_subject, html, text = ai.generate_farewell(sub.name, reply_text)
        _send(sub, farewell_subject, html, text, db)
        sub.state = DO_NOT_CONTACT
        _log(sub, "FAREWELL_SENT", db)
        print(f"[FAREWELL] ✉  {email} → DO_NOT_CONTACT (permanent)")

    # ── Day 7 sunset: no real engagement ───────────────────────────────
    elif day >= 7 and state in (EMAIL_SENT_D1, RESENT_D2, MOFU_SENT, BOFU_SENT, ENGAGED):
        subject, html, text = ai.generate_email(sub.name, stage="SUNSET", day=7)
        _send(sub, subject, html, text, db)
        sub.state = SUNSET
        _log(sub, "SUNSET_SENT", db)
        print(f"[SUNSET] ✉  {email} → SUNSET (campaign complete)")

    db.commit()




def _send(sub: Subscriber, subject: str, html: str, text: str, db):
    """Call Kishalay's mailer with AI-generated content."""
    tracking_id, status = send_email_direct(
        subscriber_email=sub.email,
        subscriber_name=sub.name,
        subject=subject,
        html_body=html,
        text_body=text,
        db=db,
    )
    return tracking_id, status


def _log(sub: Subscriber, event_type: str, db, extra: dict = None):
    import json as _json
    event = Event(
        id=str(uuid4()),
        subscriber_email=sub.email,
        tracking_id=str(uuid4()),
        event_type=event_type,
        metadata=_json.dumps(extra or {}),
    )
    db.add(event)


def _has_event(subscriber_email: str, event_type: str, db) -> bool:
    return db.query(Event).filter(
        Event.subscriber_email == subscriber_email,
        Event.event_type == event_type,
    ).first() is not None


def _get_last_reply_text(subscriber_email: str, db) -> str:
    import json as _json
    event = db.query(Event).filter(
        Event.subscriber_email == subscriber_email,
        Event.event_type == "REPLY",
    ).order_by(Event.created_at.desc()).first()
    if event:
        try:
            meta = _json.loads(event.metadata or "{}")
            return meta.get("reply_text", "")
        except Exception:
            return ""
    return ""


def _get_last_subject(subscriber_email: str, db) -> str:
    import json as _json
    event = db.query(Event).filter(
        Event.subscriber_email == subscriber_email,
        Event.event_type == "SENT",
    ).order_by(Event.created_at.desc()).first()
    if event:
        try:
            meta = _json.loads(event.metadata or "{}")
            return meta.get("subject", "")
        except Exception:
            return ""
    return ""
