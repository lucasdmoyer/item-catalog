from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Base, User, Category, Item
#from flask.ext.sqlalchemy import SQLAlchemy
from random import randint
import datetime
import random

# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
engine = create_engine('sqlite:///itemcatalogwithusers.db')

Base.metadata.bind = engine

# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
DBSession = sessionmaker(bind=engine)

session = DBSession()

User1 = User(name="Robo Barista", email="tinnyTim@udacity.com",
             picture='https://pbs.twimg.com/profile_images/2671170543/18debd694829ed78203a5a36dd364160_400x400.png')
session.add(User1)
session.commit()
user2 = User(name ="Reggie", email="dad@hey.com")
session.add(user2)
session.commit()
user3 = User(name ="Lucas", email="me@aye.com")
session.add(user3)
session.commit()

category1 = Category(name = 'Soccer')
session.add(category1)
category2 = Category(name = 'Basketball')
session.add(category2)
category3 = Category(name = 'Baseball')
session.add(category3)
category4 = Category(name = 'Frisbee')
session.add(category4)
category5 = Category(name = 'Snowboarding')
session.add(category5)
category6 = Category(name = 'Rock Climbing')
session.add(category6)
category7 = Category(name = 'Football')
session.add(category7)
category8 = Category(name = 'Skating')
session.add(category8)
category9 = Category(name = 'Hockey')
session.add(category9)
session.commit()

item1 = Item(name = 'Soccer Cleats', description = 'Has nice spikes for grass', price = '$45.50', dateAdded = datetime.date.today(), user = user3, category = category1)
session.add(item1)
item2 = Item(name = 'Shin Guards', description = 'Protects your shin for getting kicked', price = '$15.50', dateAdded = datetime.date.today(), user = user3, category = category1)
session.add(item2)
session.commit()

print 'added items!'