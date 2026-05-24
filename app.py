from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from threading import Thread

from sqlalchemy.orm import Session

from database import SessionLocal
from models import Subscriber, Event


from akash.scheduler import scheduler_loop


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    thread = Thread(target=scheduler_loop, daemon=True, name="CampaignScheduler")
    thread.start()
    yield


app = FastAPI(lifespan=lifespan)


class EnrollRequest(BaseModel):
    name: str
    email: str


class BounceRequest(BaseModel):
    email: str


@app.get("/")
def home():
    return {"status": "running", "engine": "SMTP-First Campaign Engine v1.0"}


@app.post("/enroll")
def enroll(data: EnrollRequest, db: Session = Depends(get_db)):
    existing = db.query(Subscriber).filter(Subscriber.email == data.email).first()
    if existing:
        return {"message": "already enrolled", "state": existing.state}
    subscriber = Subscriber(name=data.name, email=data.email, state="ACTIVE", current_day=0)
    db.add(subscriber)
    db.commit()
    print(f"[ENROLL] {data.name} <{data.email}>")
    return {"message": "subscriber enrolled", "email": data.email}


@app.get("/track/open/{tracking_id}")
def track_open(tracking_id: str, db: Session = Depends(get_db)):
    event_record = db.query(Event).filter(Event.tracking_id == tracking_id).first()
    subscriber_email = event_record.subscriber_email if event_record else tracking_id

    # Update subscriber state to OPENED if they were in an email-sent state
    sub = db.query(Subscriber).filter(Subscriber.email == subscriber_email).first()
    if sub and sub.state in ("ACTIVE", "EMAIL_SENT_D1", "RESENT_D2"):
        sub.state = "OPENED"
        db.commit()
        print(f"[TRACK OPEN] {subscriber_email} → OPENED")

    event = Event(
        id=str(uuid4()),
        subscriber_email=subscriber_email,
        tracking_id=tracking_id,
        event_type="OPEN",
        metadata="{}",
    )
    db.add(event)
    db.commit()

    return FileResponse("tracking/pixel.png")


@app.get("/track/click/{tracking_id}")
def track_click(tracking_id: str, db: Session = Depends(get_db)):
    event_record = db.query(Event).filter(Event.tracking_id == tracking_id).first()
    subscriber_email = event_record.subscriber_email if event_record else tracking_id

    # Update subscriber state to CLICKED
    sub = db.query(Subscriber).filter(Subscriber.email == subscriber_email).first()
    if sub and sub.state not in ("UNSUBSCRIBED", "BOUNCED", "DO_NOT_CONTACT"):
        sub.state = "CLICKED"
        db.commit()
        print(f"[TRACK CLICK] {subscriber_email} → CLICKED")

    event = Event(
        id=str(uuid4()),
        subscriber_email=subscriber_email,
        tracking_id=tracking_id,
        event_type="CLICK",
        metadata="{}",
    )
    db.add(event)
    db.commit()

    return RedirectResponse("https://dkafka.com")


@app.get("/unsubscribe/{tracking_id}")
def unsubscribe(tracking_id: str, db: Session = Depends(get_db)):
    event_record = db.query(Event).filter(Event.tracking_id == tracking_id).first()
    if event_record:
        sub = db.query(Subscriber).filter(
            Subscriber.email == event_record.subscriber_email
        ).first()
        if sub:
            sub.state = "UNSUBSCRIBED"
            db.commit()
            print(f"[UNSUBSCRIBE] {event_record.subscriber_email} → UNSUBSCRIBED")
    return {"message": "You have been unsubscribed. No more emails from us."}


@app.post("/bounce")
def bounce(data: BounceRequest, db: Session = Depends(get_db)):
    sub = db.query(Subscriber).filter(Subscriber.email == data.email).first()
    if sub:
        sub.state = "BOUNCED"
        db.commit()
        print(f"[BOUNCE] {data.email} → BOUNCED")
    return {"message": "bounce recorded"}


# ── Status endpoint (useful for demo) ─────────────────────────────────────
@app.get("/status")
def status(db: Session = Depends(get_db)):
    subs = db.query(Subscriber).all()
    return [
        {
            "email": s.email,
            "name": s.name,
            "state": s.state,
            "day": s.current_day,
        }
        for s in subs
    ]
