import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
load_dotenv()


# engine = create_engine("postgresql://postgres:qwerty@localhost:5432/postgres") #для теста поменять на "database_alembic.db"  sqlite:///database_alembic.db
engine = create_engine(os.environ["DATABASE_URL"])
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    # import  all modules here that might define models so that
    # they will be registered properly on the metadata. Otherwise
    # you will have to import them first before calling init_db()
    import models
    Base.metadata.create_all(bind=engine)