from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

from threading import Thread

from sqlalchemy.orm import Session

from database import SessionLocal
from models import Subscriber, Event
from scheduler import scheduler_loop


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    thread = Thread(target=scheduler_loop, daemon=True)
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
    return {"status": "running"}


@app.post("/enroll")
def enroll(data: EnrollRequest, db: Session = Depends(get_db)):
    subscriber = Subscriber(name=data.name, email=data.email)
    db.add(subscriber)
    db.commit()
    return {"message": "subscriber enrolled"}


@app.get("/track/open/{tracking_id}")
def track_open(tracking_id: str, db: Session = Depends(get_db)):
    event_record = db.query(Event).filter(
        Event.tracking_id == tracking_id
    ).first()

    subscriber_email = event_record.subscriber_email if event_record else tracking_id

    event = Event(
        id=str(uuid4()),
        subscriber_email=subscriber_email,
        tracking_id=tracking_id,
        event_type="OPEN"
    )
    db.add(event)
    db.commit()

    return FileResponse("tracking/pixel.png")


@app.get("/track/click/{tracking_id}")
def track_click(tracking_id: str, db: Session = Depends(get_db)):
    event_record = db.query(Event).filter(
        Event.tracking_id == tracking_id
    ).first()

    subscriber_email = event_record.subscriber_email if event_record else tracking_id

    event = Event(
        id=str(uuid4()),
        subscriber_email=subscriber_email,
        tracking_id=tracking_id,
        event_type="CLICK"
    )
    db.add(event)
    db.commit()

    return RedirectResponse("https://google.com")


@app.get("/unsubscribe/{tracking_id}")
def unsubscribe(tracking_id: str, db: Session = Depends(get_db)):
    event = db.query(Event).filter(
        Event.tracking_id == tracking_id
    ).first()

    if event:
        subscriber = db.query(Subscriber).filter(
            Subscriber.email == event.subscriber_email
        ).first()

        if subscriber:
            subscriber.state = "UNSUBSCRIBED"
            db.commit()

    return {"message": "unsubscribed"}


@app.post("/bounce")
def bounce(data: BounceRequest, db: Session = Depends(get_db)):
    subscriber = db.query(Subscriber).filter(
        Subscriber.email == data.email
    ).first()

    if subscriber:
        subscriber.state = "BOUNCED"
        db.commit()

    return {"message": "bounce recorded"}
