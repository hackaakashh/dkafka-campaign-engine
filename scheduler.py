import time

from config import DAY_DURATION_MS, SEND_THROTTLE_SECONDS
from database import SessionLocal
from models import Subscriber
from mailer import send_email


def scheduler_loop():
    while True:
        db = SessionLocal()
        try:
            subscribers = db.query(Subscriber).filter(
                Subscriber.state == "ACTIVE"
            ).all()

            for subscriber in subscribers:
                try:
                    send_email(subscriber, "Day 1", "day1.html", "day1.txt")
                except Exception as e:
                    print(f"Failed to send to {subscriber.email}: {e}")

                time.sleep(SEND_THROTTLE_SECONDS)

        finally:
            db.close()

        time.sleep(DAY_DURATION_MS / 1000)
