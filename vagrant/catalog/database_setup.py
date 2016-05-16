import sys
sys.path.insert(0, 'libs')

from bfs_core_database import Base, User, Image, Catalog, Catagory, Item
from sqlalchemy import create_engine

engine = create_engine('sqlite:///catalog.db')
Base.metadata.create_all(engine)
