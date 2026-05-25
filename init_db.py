from database import Base, engine
import models  # noqa: F401 - ensures models are registered on Base

Base.metadata.create_all(bind=engine)

print("Tables created.")
