from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import (sessionmaker, relationship, backref)
from sqlalchemy import create_engine, engine
from sqlalchemy.sql import func
import os
import logging
import gcloud
import pymysql 


env = os.environ.get("ENV")

db_user = os.environ.get("DB_USER")
db_name = os.environ.get("DB_NAME")
host = os.environ.get("HOST")
port = os.environ.get("DB_PORT")

if env == "GCLOUD":
    cloud_sql_connection_name = os.environ.get("CLOUD_SQL_CONNECTION_NAME")
    project_id = os.environ.get('GCLOUD_PROJECT_ID')
    gcl = gcloud.Gcloud(project_id)

    db_pass = gcl.access_secret_version(secret_id="LEADERBOARD-DB_PASS")

    url = engine.url.URL(
            drivername="mysql+pymysql",
            username=db_user,  # e.g. "my-database-user"
            password=db_pass,
            host=host,
            port=port,  # e.g. "my-database-password"
            database=db_name,  # e.g. "my-database-name"
            query={
                "unix_socket": "/cloudsql/{}".format(cloud_sql_connection_name)  # i.e "<PROJECT-NAME>:<INSTANCE-REGION>:<INSTANCE-NAME>"
            }
        )
else:
    db_pass = os.environ.get('DB_PASS')
    url = engine.url.URL(
                    drivername="mysql+pymysql",
                    username=db_user,
                    password=db_pass,
                    host=host,
                    port=port,
                    database=db_name
                )



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
            url,
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
    performed_activities = relationship("Performed_Activity", cascade="all, delete-orphan")


    def __init__(self, activity_name, points, author_user_id, leaderboard_id):
        self.activity_name = activity_name
        self.points = points
        self.author_user_id = author_user_id
        self.leaderboard_id =leaderboard_id

    @establish_session
    def save_activity(self, session):
        session.add(self)
        session.commit()
        session.close()

    @establish_session
    def delete_activity(self, session):
        activity = session.merge(self)
        session.delete(activity)
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

@establish_session
def get_leaderboard_by_activity_id(session, activity_id:int):
    activity = session.query(Activity).filter_by(id=activity_id).first()
    leaderboard = session.query(Leaderboard).filter_by(id = activity.leaderboard_id).first()
    return leaderboard


@establish_session
def get_leaderboard_activities(session, leaderboard_id:int):
    result = session.query(Activity).filter_by(leaderboard_id=leaderboard_id)
    return result

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


@establish_session
def leaderboard_has_activities(session, leaderboard_id:int):
    exists = False
    q = session.query(Activity).filter_by(leaderboard_id=leaderboard_id).count()
    if q:
        exists = True
    return exists

@establish_session
def get_leaderboard_score(session, leaderboard_id:int):
    qeury = f'''
    SELECT users.name, COALESCE(SUM(a.points), 0) as 'points'
    FROM `leaderboard`.`leaderboards` lb
    JOIN `leaderboard`.`participants` p 
        ON lb.id = p.leaderboard_id
    JOIN `leaderboard`.`users` users
        ON p.user_id = users.id
    LEFT JOIN `leaderboard`.`performed_activity` pa
        ON p.id = pa.participant_id
    LEFT JOIN `leaderboard`.`activities` a
        ON pa.activity_id = a.id 
    WHERE lb.id = {leaderboard_id}
    GROUP BY p.id
    ORDER BY COALESCE(SUM(a.points), 0) DESC
    '''
    result = session.execute(qeury)
    return result

class Participant(Base):

    __tablename__ = 'participants'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    leaderboard_id = Column(BigInteger, ForeignKey('leaderboards.id'))
    user_id = Column(BigInteger, ForeignKey('users.id'))
    time_created = Column(DateTime(timezone=True), nullable=False, default=func.now())

    performed_activities = relationship("Performed_Activity", cascade="all, delete-orphan")


    @establish_session
    def save_participant(self, session):
        session.merge(self)
        session.commit()
        session.close()

@establish_session
def get_participant_by_user_id_and_leaderboard_id(session, user_id:int, leaderboard_id:int):
    participant = session.query(Participant).filter_by(leaderboard_id=leaderboard_id, user_id=user_id).first()
    return participant

@establish_session
def get_participants_by_leaderboard_id(session, leaderboard_id:int):
    participants = session.query(Participant).filter_by(leaderboard_id=leaderboard_id)
    return participants


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

    activities = relationship('Activity',
                                backref=backref('performed_activities_act', cascade="all, delete-orphan")
                            )
    
    participants = relationship('Participant',
                                backref=backref('performed_activities_partic', cascade="all, delete-orphan")
                            )
     

    def __init__(self, activity_id:int, participant_id:id):
        self.activity_id = activity_id
        self.participant_id = participant_id

    @establish_session
    def save_performed_activity(self, session):
        session.merge(self)
        session.commit()
        session.close()

    @establish_session
    def delete_performed_activity(self, session):
        performed_activity = session.merge(self)
        session.delete(performed_activity)
        session.commit()
        session.close()


@establish_session
def get_performed_activities(session, user_id:int, leaderboard_id:int):
    """
    Returns Activities performed by user
    """
    query = f'''
        SELECT pa.id, pa.time_created as 'time', a.activity_name as 'name'
        FROM `leaderboard`.`performed_activity` pa
        JOIN `leaderboard`.`activities` a
            ON a.id = pa.activity_id
        JOIN `leaderboard`.`participants` p
            ON p.id = pa.participant_id
        JOIN `leaderboard`.`users` u 
            ON u.id = p.user_id    
        JOIN `leaderboard`.`leaderboards` ld
            ON ld.id = a.leaderboard_id
        WHERE u.id = {user_id}
        AND ld.id = {leaderboard_id};
    '''
    result = session.execute(query)
    return result

@establish_session
def get_performed_activity_by_id(session, id:int):
    """
    Returns performed Activity by it
    """
    performed_activity = session.query(Performed_Activity).filter_by(id=id).first()
    return performed_activity        


@establish_session
def get_leaderboard_log(session, leaderboard_id:int, count:int):
    """
    Returns Activities Execution records from leaderboard
    """
    query = f'''SELECT u.name, a.activity_name, a.points, pa.time_created
            FROM `leaderboard`.`performed_activity` pa
            JOIN `leaderboard`.`activities` a
                ON a.id = pa.activity_id
            JOIN `leaderboard`.`participants` p
                ON p.id = pa.participant_id
            JOIN `leaderboard`.`users` u
                ON u.id = p.user_id
            WHERE a.leaderboard_id = {leaderboard_id}
            ORDER BY pa.time_created DESC
            LIMIT {count};'''
        
    result = session.execute(query)
    return result

# TODO: Check how to create base class with save_entity_name(self) method in order not 
# to repeat same code in each class