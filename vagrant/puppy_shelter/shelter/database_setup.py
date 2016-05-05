import sys
from sqlalchemy import Column, ForeignKey, Integer, String, Date, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class Shelter(Base):
    __tablename__ = "shelter"
    id = Column(Integer, primary_key = True)
    name = Column(String(32), nullable = False)
    address = Column(String(64), nullable = False)
    city = Column(String(32), nullable = False)
    state = Column(String(2), nullable = False)
    zipCode = Column(String(11), nullable = False)
    website = Column(String(128))

class Puppy(Base):
    __tablename__ = "puppy"
    id = Column(Integer, primary_key = True)
    name = Column(String(32))
    dateOfBirth = Column(Date())
    gender = Column(String(6))
    weight = Column(Float)
    shelter_id = Column(Integer, ForeignKey('shelter.id'))
    shelter = relationship(Shelter)
    
# Initialize Engine DB

engine = create_engine('sqlite:///shelter.db')

Base.metadata.create_all(engine)

