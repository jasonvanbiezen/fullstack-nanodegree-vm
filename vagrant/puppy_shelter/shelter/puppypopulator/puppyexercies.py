from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from puppies import Base, Shelter, Puppy
import datetime

engine = create_engine('sqlite:///puppyshelter.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind = engine)
session = DBSession()

puppiesAlph = session.query(Puppy).order_by('puppy.name').all()
for puppy in puppiesAlph:
    print(puppy.name)

print('-' * 79)
sixMonths = datetime.datetime.utcnow() - datetime.timedelta(days=365/2)
puppies6mo = session.query(Puppy).filter(Puppy.dateOfBirth > sixMonths).order_by(Puppy.dateOfBirth.desc()).all()
for puppy in puppies6mo:
    print(puppy.name, puppy.dateOfBirth)

print('-' * 79)
pWeight = session.query(Puppy).order_by(Puppy.weight.asc()).all()
for puppy in pWeight:
    print(puppy.name, puppy.weight)

print('-' * 79)
#pShelter = session.query(Puppy).join(Shelter).order_by(Shelter.id).all()
pShelter = session.query(Puppy).join(Shelter, Puppy.shelter_id == Shelter.id).order_by(Puppy.shelter_id).all()

for puppy in pShelter:
    print(puppy.name, puppy.shelter.name)
