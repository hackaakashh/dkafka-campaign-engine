"""
Reply Detector — polls reply inbox via IMAP to detect real replies.
Also provides TestReplyHarness for demo simulation without IMAP.
"""

import imaplib
import email as email_lib
import time
import threading
from email.header import decode_header as _decode_header

from config import IMAP_HOST, IMAP_USER, IMAP_PASS, REPLY_POLL_INTERVAL
from database import SessionLocal
from models import Subscriber, Event
from uuid import uuid4

from aakash.state_machine import (
    TERMINAL_STATES, REPLIED_POSITIVE, REPLIED_NEGATIVE,
    OPENED, BOUNCED, UNSUBSCRIBED
)


# ──────────────────────────────────────────────────────────────────────────
# Live IMAP detector
# ──────────────────────────────────────────────────────────────────────────
class ReplyDetector:
    """
    Polls REPLY_TO inbox every REPLY_POLL_INTERVAL seconds.
    Classifies unseen emails and updates subscriber state.
    """

    def __init__(self, ai_agent):
        self.ai = ai_agent
        self._running = False
        self._thread = None

    def start(self):
        if not IMAP_USER or not IMAP_PASS:
            print("[REPLY DETECTOR] IMAP not configured. "
                  "Use TestReplyHarness to simulate replies.")
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="ReplyDetector"
        )
        self._thread.start()
        print(f"[REPLY DETECTOR] Started — polling every {REPLY_POLL_INTERVAL}s")

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            try:
                self._check_inbox()
            except Exception as e:
                print(f"[REPLY DETECTOR] Poll error: {e}")
            time.sleep(REPLY_POLL_INTERVAL)

    def _check_inbox(self):
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(IMAP_USER, IMAP_PASS)
        mail.select("inbox")
        status, data = mail.search(None, "UNSEEN")
        if status != "OK" or not data[0]:
            mail.logout()
            return

        for eid in data[0].split():
            try:
                _, msg_data = mail.fetch(eid, "(RFC822)")
                msg = email_lib.message_from_bytes(msg_data[0][1])
                from_addr = email_lib.utils.parseaddr(msg.get("From", ""))[1].lower()
                body = self._extract_body(msg)

                db = SessionLocal()
                try:
                    sub = db.query(Subscriber).filter(
                        Subscriber.email == from_addr
                    ).first()
                    if sub and sub.state not in TERMINAL_STATES:
                        self._process_reply(sub, body, db)
                finally:
                    db.close()

            except Exception as e:
                print(f"[REPLY DETECTOR] Error on message {eid}: {e}")

        mail.logout()

    def _process_reply(self, sub, body: str, db):
        sentiment = self.ai.classify_reply(body)
        old_state = sub.state

        if sentiment == "negative":
            sub.state = REPLIED_NEGATIVE
        else:
            sub.state = REPLIED_POSITIVE

        event = Event(
            id=str(uuid4()),
            subscriber_email=sub.email,
            tracking_id=str(uuid4()),
            event_type="REPLY",
            metadata=f'{{"reply_text": {repr(body[:400])}, "sentiment": "{sentiment}"}}',
        )
        db.add(event)
        db.commit()
        print(f"[REPLY] {sub.email} ({sentiment}) | {old_state} → {sub.state}")

    @staticmethod
    def _extract_body(msg) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload.decode("utf-8", errors="ignore")[:800]
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                return payload.decode("utf-8", errors="ignore")[:800]
        return ""


# ──────────────────────────────────────────────────────────────────────────
# Test harness for demo (no IMAP needed)
# ──────────────────────────────────────────────────────────────────────────
class TestReplyHarness:
    """
    Simulate events from the terminal during a live demo run.
    Called by demo_console.py
    """

    def __init__(self, ai_agent):
        self.ai = ai_agent

    def simulate_reply(self, subscriber_email: str, reply_text: str):
        db = SessionLocal()
        try:
            sub = db.query(Subscriber).filter(
                Subscriber.email == subscriber_email
            ).first()
            if not sub:
                print(f"[TEST] Not found: {subscriber_email}")
                return
            if sub.state in TERMINAL_STATES:
                print(f"[TEST] {subscriber_email} is terminal ({sub.state})")
                return

            sentiment = self.ai.classify_reply(reply_text)
            old_state = sub.state
            sub.state = REPLIED_NEGATIVE if sentiment == "negative" else REPLIED_POSITIVE

            event = Event(
                id=str(uuid4()),
                subscriber_email=sub.email,
                tracking_id=str(uuid4()),
                event_type="REPLY",
                metadata=(
                    f'{{"reply_text": {repr(reply_text[:300])}, '
                    f'"sentiment": "{sentiment}", "simulated": true}}'
                ),
            )
            db.add(event)
            db.commit()
            print(f"[TEST REPLY] {subscriber_email}")
            print(f"  text:      '{reply_text[:70]}'")
            print(f"  sentiment: {sentiment}")
            print(f"  state:     {old_state} → {sub.state}")
        finally:
            db.close()

    def simulate_open(self, subscriber_email: str):
        db = SessionLocal()
        try:
            sub = db.query(Subscriber).filter(
                Subscriber.email == subscriber_email
            ).first()
            if not sub:
                print(f"[TEST] Not found: {subscriber_email}")
                return
            if sub.state in ("EMAIL_SENT_D1", "RESENT_D2", "ACTIVE"):
                old = sub.state
                sub.state = OPENED
                event = Event(
                    id=str(uuid4()),
                    subscriber_email=sub.email,
                    tracking_id=str(uuid4()),
                    event_type="OPEN",
                    metadata='{"simulated": true}',
                )
                db.add(event)
                db.commit()
                print(f"[TEST OPEN] {subscriber_email}: {old} → OPENED")
            else:
                print(f"[TEST OPEN] {subscriber_email} already in state {sub.state}")
        finally:
            db.close()

    def simulate_click(self, subscriber_email: str):
        db = SessionLocal()
        try:
            sub = db.query(Subscriber).filter(
                Subscriber.email == subscriber_email
            ).first()
            if not sub:
                print(f"[TEST] Not found: {subscriber_email}")
                return
            if sub.state not in TERMINAL_STATES:
                old = sub.state
                sub.state = "CLICKED"
                event = Event(
                    id=str(uuid4()),
                    subscriber_email=sub.email,
                    tracking_id=str(uuid4()),
                    event_type="CLICK",
                    metadata='{"simulated": true}',
                )
                db.add(event)
                db.commit()
                print(f"[TEST CLICK] {subscriber_email}: {old} → CLICKED")
        finally:
            db.close()

    def simulate_bounce(self, subscriber_email: str):
        db = SessionLocal()
        try:
            sub = db.query(Subscriber).filter(
                Subscriber.email == subscriber_email
            ).first()
            if not sub:
                print(f"[TEST] Not found: {subscriber_email}")
                return
            old = sub.state
            sub.state = BOUNCED
            event = Event(
                id=str(uuid4()),
                subscriber_email=sub.email,
                tracking_id=str(uuid4()),
                event_type="BOUNCE",
                metadata='{"simulated": true}',
            )
            db.add(event)
            db.commit()
            print(f"[TEST BOUNCE] {subscriber_email}: {old} → BOUNCED (all sends stopped)")
        finally:
            db.close()

    def print_status(self):
        db = SessionLocal()
        try:
            subs = db.query(Subscriber).all()
            print("\n┌─ SUBSCRIBER STATUS ──────────────────────────────────")
            for s in subs:
                print(f"│  {s.name:<22} {s.email}")
                print(f"│  State: {s.state:<25} Day: {s.current_day}")
            print("└─────────────────────────────────────────────────────\n")
        finally:
            db.close()

    def print_events(self):
        db = SessionLocal()
        try:
            events = db.query(Event).order_by(Event.created_at.desc()).limit(20).all()
            print("\n┌─ RECENT EVENTS ──────────────────────────────────────")
            for e in reversed(events):
                print(f"│  {str(e.created_at)[11:19]}  {e.event_type:<16}  {e.subscriber_email}")
            print("└─────────────────────────────────────────────────────\n")
        finally:
            db.close()

