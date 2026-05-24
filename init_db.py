from database import Base, engine
import models  # noqa: ensures models are registered

Base.metadata.create_all(bind=engine)
print("Tables created (subscribers + events with new columns).")
