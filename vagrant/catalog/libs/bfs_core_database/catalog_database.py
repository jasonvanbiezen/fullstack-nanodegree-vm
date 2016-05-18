# Written by Jason van Biezen <github.com/jasonvanbiezen>, May 2016.
# This package was written to satisfy the Nanodegree requirements of Udacity's
# Fullstack program.  This package, and all project code hosted publicly
# on my github.com page is free to use.  I only ask that, if my work
# is useful to you, or if you reuse my code, please give me credit
# in your readme.  

from sqlalchemy import Column, ForeignKey, Integer, String, Float, Boolean, Text
from sqlalchemy.dialects.sqlite import BLOB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import validates
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))

    @validates("email")
    def validate_email(self, key, email_address):
        assert '@' in email_address and '.' in email_address
        return email_address

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'name'         : self.name,
           'id'           : self.id,
           'email'        : self.email,
           'picture'      : self.picture,
       }

class Image(Base):
    __tablename__ = "image"

    id = Column(Integer, primary_key=True)
    filename = Column(String(250), nullable=False)

class Catalog(Base):
    __tablename__ = "catalog"

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    public = Column(Boolean)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    header_image = Column(String(250))

class Catagory(Base):
    __tablename__ = "catagory"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    description = Column(Text, default='')
    catalog_id = Column(Integer, ForeignKey('catalog.id'))
    catalog = relationship(Catalog)
    catagory_image = Column(String(250))

class Item(Base):
    __tablename__ = "item"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    description = Column(Text, default='')
    quantity = Column(Integer, default=0)
    price = Column(Float(precision=2), default=0.0)
    row = Column(Integer)
    bin = Column(Integer)
    catagory_id = Column(Integer, ForeignKey('catagory.id'))
    catagory = relationship(Catagory)
    item_image = Column(String(250))

