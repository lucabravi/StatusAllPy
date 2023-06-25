import datetime
import json
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Query

conn = SQLAlchemy()
Base = conn.Model

logger = logging.getLogger(__name__)


def init_db(app, echo=False):
    app.config["DB_USER"] = os.environ.get("DB_USER")
    app.config["DB_PASSWORD"] = os.environ.get("DB_PASSWORD")
    app.config["DB_HOST"] = os.environ.get("DB_HOST")
    app.config["DB_PORT"] = os.environ.get("DB_PORT")
    app.config["DB_NAME"] = os.environ.get("DB_NAME")

    app.config[
        'SQLALCHEMY_DATABASE_URI'] = f'mysql://{app.config["DB_USER"]}:{app.config["DB_PASSWORD"]}@{app.config["DB_HOST"]}:{app.config["DB_PORT"]}/{app.config["DB_NAME"]}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = echo
    conn.init_app(app)

    Base.metadata.create_all(conn.engine)
    preload_data()


def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance


def query_to_dict(query, key=None):
    if not isinstance(query, Query):
        raise ValueError("L'argomento deve essere un oggetto Query di SQLAlchemy.")

    results = query.all()
    if key is None:
        dict_results = []
        for row in results:
            json_result = {}
            for column_name in row._fields:
                column_name = getattr(row, column_name)
                if isinstance(column_value, datetime.datetime):
                    column_value = column_value.strftime('%Y-%m-%d %H:%M:%S')
                json_result[column_name] = column_value
            dict_results.append(json_result)
    else:
        dict_results = {}
        for row in results:
            json_result = {}
            for column_name in row._fields:
                if column_name == key:
                    continue
                column_value = getattr(row, column_name)
                if isinstance(column_value, datetime.datetime):
                    column_value = column_value.strftime('%Y-%m-%d %H:%M:%S')
                json_result[column_name] = column_value
            dict_results[getattr(row, key)] = json_result

    return dict_results


from .device import Device
from .services import Service, PingService, DockerService, DiskService

import database.data_init


def preload_data():
    for group in data_init.devices:
        for device in data_init.devices[group]:
            if Device.query.filter_by(ip=device[0]).first() is None:
                new_device = Device(ip=device[0], _name=device[1], group=group, last_update=None)
                conn.session.add(new_device)
    conn.session.commit()


def delete_old_records():
    logger.info('DB: Cleaning up old records')

    threshold_date = datetime.datetime.now() - datetime.timedelta(days=7)
    # records_to_delete = Device.query.filter(Device.last_update < threshold_date)
    # records_to_delete.delete()
    records_to_delete = Service.query.filter(Service.last_update < threshold_date)
    records_to_delete.delete()

    conn.session.commit()
