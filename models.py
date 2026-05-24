from sqlalchemy import Column, String, DateTime, Integer, Text
from sqlalchemy.sql import func

from database import Base


class Subscriber(Base):
    __tablename__ = "subscribers"

    email = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    state = Column(String, default="ACTIVE")
    current_day = Column(Integer, default=0)
    conversation_history = Column(Text, default="[]")
    created_at = Column(DateTime, server_default=func.now())
    last_event_at = Column(DateTime, onupdate=func.now())


class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True)
    subscriber_email = Column(String, nullable=False)
    tracking_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    metadata = Column(Text, default="{}")
    created_at = Column(DateTime, server_default=func.now())
