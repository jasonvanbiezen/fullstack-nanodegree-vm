from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem
engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind = engine)
session = DBSession()

firstResult = session.query(Restaurant).first()
print(firstResult.name)

print("All restaurants")

restaurants = session.query(Restaurant).all()

for r in restaurants:
    print(r.name)
