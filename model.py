from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import (sessionmaker, relationship)
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


class Activity(Base):
    __tablename__ = 'activities'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    activity_name = Column(String(255))
    time_created = Column(DateTime(timezone=True), nullable=False, default=func.now() )
    points = Column(Integer)

    author_user_id = Column(BigInteger, ForeignKey('users.id'))
    leaderboard_id = Column(BigInteger, ForeignKey('leaderboards.id'))

    # Relationships 
    performed_activities = relationship("Performed_Activity")


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
    return result

@ensure_connection
def delete_activity_by_id(session, activity_id:int):
    activity = session.query(Activity).filter_by(id=activity_id).first()
    if activity:
        session.delete(activity)
    session.close()

class Leaderboard(Base):

    __tablename__ = 'leaderboards'

    def __init__(self, id, name):
        self.id = id
        self.name = name 

    # Equal to Chat_Id
    id = Column(BigInteger, primary_key=True)
    # Name of the Leaderboard. Equal to the name of the Chat conversation 
    name = Column(String(255))
    time_created = Column(DateTime(timezone=True), nullable=False, default=func.now())

    #Relationships
    participants = relationship("Participant")
    activities = relationship("Activity")

    @establish_session
    def save_leaderboard(self, session):
        session.merge(self)
        session.commit()
        session.close()


@establish_session
def get_leaderboard_by_id(session, leaderboard_id:int):
    leaderboard = session.query(Leaderboard).filter_by(id=leaderboard_id).first()
    return leaderboard


class Participant(Base):

    __tablename__ = 'participants'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    leaderboard_id = Column(BigInteger, ForeignKey('leaderboards.id'))
    user_id = Column(BigInteger, ForeignKey('users.id'))
    time_created = Column(DateTime(timezone=True), nullable=False, default=func.now())

    performed_activities = relationship("Performed_Activity")

    @establish_session
    def save_participant(self, session):
        session.merge(self)
        session.commit()
        session.close()

@establish_session
def get_participant_by_user_id_and_leaderboard_id(session, user_id:int, leaderboard_id:int):
    participant = session.query(Participant).filter_by(leaderboard_id=leaderboard_id, user_id=user_id).first()
    return participant

class User(Base):

    __tablename__ = 'users'
    
    #Equal to User_ID in telegram 
    id = Column(BigInteger, primary_key=True)
    #Equal to the user name of the user in Telegram
    name =  Column(String(255))
    time_create = Column(DateTime(timezone=True), nullable=False, default=func.now())
    #TODO: Potentially add some additional data about user

    #Relationships
    participants = relationship("Participant")
    created_activities = relationship("Activity")

    def __init__(self, name:str, id:int):
        self.name = name
        self.id = id

    @establish_session
    def save_user(self, session):
        session.merge(self)
        session.commit()
        session.close()

@establish_session
def get_user_by_id(session, id:int):
    user = session.query(User).filter_by(id=id).first()
    return user


class Performed_Activity(Base):

    __tablename__ = 'performed_activity'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    time_created = Column(DateTime(timezone=True), nullable=False, default=func.now())

    #Relationships
    activity_id = Column(BigInteger, ForeignKey('activities.id'))
    participant_id = Column(BigInteger, ForeignKey('participants.id'))

    @establish_session
    def save_performed_activity(self, session):
        session.merge(self)
        session.commit()
        session.close()




# TODO: Check how to create base class with save_entity_name(self) method in order not 
# to repeat same code in each class