from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

engine = create_engine('sqlite:///ping_results.db', echo=False)
Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()


def init_db():
    Base.metadata.create_all(engine)
    preload_data()


from .device import Device
from .container import Container

import database.data_init


def preload_data():
    for group in data_init.devices:
        for device in data_init.devices[group]:
            if session.query(Device).filter_by(ip=device[0]).first() is None:
                session.add(Device(ip=device[0], name=device[1], group=group, last_update=None, status=False))
                session.commit()
