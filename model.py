from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, BigInteger, TIMESTAMP


Base = declarative_base()

class Activity(Base):
    __tablename__ = activities

    activity_id = Column(BigInteger, primery_key=True)
    activity_name = Column(String)
    time_created = Column(TIMESTAMP)
    points = Column(Integer)
    author = Column(String)

     def __repr__(self):
        return "<Activity(activity_name='%s', time_created='%s', points='%s', author='%s')>" % (
                             self.name, self.fullname, self.nickname, self.author)
