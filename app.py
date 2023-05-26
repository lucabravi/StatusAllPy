import datetime
import logging
from subprocess import PIPE
import threading
import os
import platform
import asyncio

from flask import Flask, render_template, request

from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, func, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

from device_init import init_devices

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

cur_dir = os.path.dirname(os.path.abspath(__file__))

engine = create_engine(f'sqlite:///{cur_dir}/ping_results.db', echo=False)
Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()


class Device(Base):
    id = Column(Integer, primary_key=True)
    ip = Column(String, nullable=False, unique=True)
    _name = Column(String, nullable=False, unique=True)
    group = Column(String, nullable=False, default='client')
    last_update = Column(DateTime, nullable=True)
    status = Column(Boolean, default=False)

    @property
    def name(self):
        if self._name:
            return f'{".".join(self.ip.split(".")[-2:]) + " " if self.ip.startswith("192.168") else ""}{self._name}'
        else:
            return self.ip

    @name.setter
    def name(self, value):
        self._name = value


class Container(Base):
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id'))
    name = Column(String(100))
    image = Column(String(100))
    uptime = Column(String(100))
    last_update = Column(DateTime, nullable=True)

    device = relationship('Device')

    def __init__(self, device, name, image, uptime):
        self.device = device
        self.name = name
        self.image = image
        self.uptime = uptime


Base.metadata.create_all(engine)
devices = None


async def ping_device(device):
    while True:
        try:
            if platform.system() == 'Windows':
                process = await asyncio.create_subprocess_exec('ping', '-n', '1', device.ip, stdout=PIPE, stderr=PIPE,
                                                               text=False)
            else:
                process = await asyncio.create_subprocess_exec('ping', '-c', '1', '-W', '0.3', device.ip,
                                                               stdout=PIPE, stderr=PIPE, text=False)
            stdout, stderr = await process.communicate()
            device.last_check = datetime.datetime.now()
            device.status = process.returncode == 0
            session.commit()

            logger.info(f"{device.name}: {device.status}")

        except Exception as e:
            logger.error(e)

        finally:
            await asyncio.sleep(30)


async def start_ping_checks():
    global devices
    for group in init_devices:
        for device in init_devices[group]:
            if session.query(Device).filter_by(ip=device[0]).first() is None:
                session.add(Device(ip=device[0], name=device[1], group=group, last_check=None, status=False))
                session.commit()

    devices = session.query(Device).order_by(Device.id).all()

    tasks = []
    for device in devices:
        task = asyncio.create_task(ping_device(device))
        tasks.append(task)

    await asyncio.gather(*tasks)


@app.route('/')
def index():
    groups = [{'name': g[0], 'count': g[1], 'online': g[2]}
              for g in
              session.query(Device.group, func.count(Device._name), func.sum(func.cast(Device.status, Integer)))
              .group_by(Device.group)
              .all()]

    devices = {g['name']: session.query(Device).filter_by(group=g['name']).all() for g in groups}

    return render_template('index.html', groups=groups, devices=devices)


if __name__ == '__main__':
    use_relaoder = True
    if not use_relaoder or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        loop = asyncio.new_event_loop()
        loop.create_task(start_ping_checks())
        thread = threading.Thread(target=loop.run_forever)
        thread.start()

    logger.info('run app')
    app.run(host='127.0.0.1', debug=True, port=5000, use_reloader=use_relaoder)
