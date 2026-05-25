from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func

from database import Base


class Subscriber(Base):
    __tablename__ = "subscribers"

    email = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    state = Column(String, default="ACTIVE")
    created_at = Column(DateTime, server_default=func.now())


class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True)
    subscriber_email = Column(String, nullable=False)
    tracking_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
