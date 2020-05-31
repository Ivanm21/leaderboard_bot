from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, BigInteger, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, engine
from sqlalchemy.sql import func
import os
import logging


db_user = os.environ.get("DB_USER")
db_pass = os.environ.get("DB_PASS")
db_name = os.environ.get("DB_NAME")
host = os.environ.get("HOST")
port = os.environ.get("PORT")
cloud_sql_connection_name = os.environ.get("CLOUD_SQL_CONNECTION_NAME")

logger = logging.getLogger()

Base = declarative_base()


def ensure_connection(func):
    """
    Decorator to connect to db
    """
    def inner(*args, **kwargs):
        db = create_engine(
    # Equivalent URL:
    # mysql+pymysql://<db_user>:<db_pass>@/<db_name>?unix_socket=/cloudsql/<cloud_sql_instance_name>
            engine.url.URL(
                drivername="mysql+pymysql",
                username=db_user,
                password=db_pass,
                host=host,
                port=port,
                database=db_name,
                # query={"unix_socket": "/cloudsql/{}".format(cloud_sql_connection_name)},
            ),
            pool_size=5,
            max_overflow=2,
            pool_timeout=30,  # 30 seconds
            pool_recycle=1800,  # 30 minutes

        )

       
        kwargs['db'] = db
        res = func(*args, **kwargs)
        return res

    return inner

@ensure_connection
def establish_session(func, db):
    """
    Decorator to establish session.
    Should be used only with ensure_connection decorator
    """
    def inner(*args, **kwargs):
        Session = sessionmaker(bind=db)
        session = Session()
        kwargs['session'] = session
        res = func(*args, **kwargs)
        return res

    return inner

@ensure_connection
def init_db(db):
    Base.metadata.create_all(db)


#TODO: Connect Activity entity to Leaderboard
class Activity(Base):
    __tablename__ = 'activities'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    activity_name = Column(String(255))
    time_created = Column(DateTime(timezone=True), nullable=False, default=func.now() )
    points = Column(Integer)
    author_user_id = Column(Integer)

    def __init__(self, activity_name, points, author_user_id):
        self.activity_name = activity_name
        self.points = points
        self.author_user_id = author_user_id

    @establish_session
    def save_activity(self, session):
        session.add(self)
        session.commit()
        session.close()

    @establish_session
    def delete_activity(self, session):
        session.delete(self)
        session.commit()
        session.close()

    def __repr__(self):
        return "<Activity(activity_name='%s', time_created='%s', points='%s', author_user_id='%s')>" % (
                             self.activity_name, self.time_created, self.points, self.author_user_id)

@establish_session
def get_activities_by_user_id(session, user_id:int):
    result = session.query(Activity).filter_by(author_user_id=user_id)
    session.close()
    return result

@establish_session
def get_activity_by_id(session, activity_id:int):
    result = session.query(Activity).filter_by(id=activity_id).first() 
    session.close()
    return result

@ensure_connection
def delete_activity_by_id(session, activity_id:int):
    activity = session.query(Activity).filter_by(id=activity_id).first()
    if activity:
        session.delete(activity)
    session.close()

#TODO: Create Leaderboard Entity 
# id = chat_id 
# should be created by start command 

#TODO: Create Participant (User in leaderboard) entity
# All chat Users should automatically added to the leaderboard

#TODO: Create User entity 

#TODO: Implement Performed_Activity entity
