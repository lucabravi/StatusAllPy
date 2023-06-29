import datetime
from operator import and_

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Index, desc, func
from sqlalchemy.orm import relationship, with_polymorphic

from . import conn, Base, get_or_create, logger


class Service(Base):
    __tablename__ = 'services'

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(30))
    subname = Column(String(30))
    _status = Column(Boolean)
    last_update = Column(DateTime, nullable=False, default=datetime.datetime.now)
    last_changed = Column(DateTime, nullable=False, default=datetime.datetime.now)

    device = relationship('Device', backref='services')

    __table_args__ = (
        Index('idx_deviceid_name_subname_lastupdate', device_id, name, subname, last_update),
    )

    __mapper_args__ = {
        'polymorphic_identity': 'service',
        "with_polymorphic": "*",
        'polymorphic_on': name,
    }

    def _analyze_status(self, **kwargs):
        self._set_status(kwargs['status'])

    def _set_status(self, status):
        self.last_update = datetime.datetime.now()
        if status != self._status:
            self.last_changed = datetime.datetime.now()
            self._status = status

    @property
    def status(self):
        if self.last_update is None:
            return False
        if (datetime.datetime.now() - self.last_update) < datetime.timedelta(minutes=5):
            return self._status
        return False

    @status.setter
    def status(self, status):
        self._set_status(status)

    @classmethod
    def update_status(cls, device, *args, **kwargs):
        last_update = kwargs.pop("last_update") if "last_update" in kwargs else datetime.datetime.now()
        device.last_update = last_update

        try:
            service = get_or_create(conn.session, cls, device=device, name=cls.__name__, **kwargs)
            with conn.session.begin():
                service._analyze_status(**kwargs)
                conn.session.add(device)
                conn.session.commit()
        except Exception as e:
            logger.error(f'Service | update_status | {e}')
            conn.session.rollback()
            raise

    @classmethod
    def get_services_by_device(cls, device_id):
        # all_kind_services = with_polymorphic(Service, [PingService, DockerContainer])

        subquery = (
            conn.session.query(Service.name, Service.subname, func.max(Service.last_update).label('max_last_update'))
            .filter(Service.device_id == device_id)
            .group_by(Service.name, Service.subname)
            .subquery()
        )

        result = conn.session.query(Service) \
            .join(subquery, and_(Service.name == subquery.c.name, Service.last_update == subquery.c.max_last_update)) \
            .filter(Service.device_id == device_id)

        return result

    def to_dict(self):
        return {
            'name': self.name,
            'subname': self.subname,
            'status': self.status,
            'last_update': self.last_update,
            'last_changed': self.last_changed
        }

    def __repr__(self):
        return f"<Service(name='{self.name}', status='{self._status}')>"


class PingService(Service):
    __tablename__ = 'ping_services'
    id = Column(Integer, ForeignKey('services.id', ondelete='CASCADE'), primary_key=True)
    response_time = Column(Integer, default=-1, nullable=False)

    __mapper_args__ = {
        "polymorphic_load": "inline",
        'polymorphic_identity': 'PingService'
    }

    @classmethod
    def get_ping_status(cls, device_id):
        return conn.session.query(cls).filter_by(device_id=device_id).order_by(desc(cls.last_update)).first()

    @classmethod
    def update_status(cls, device, *args, **kwargs):
        try:
            device.last_update = kwargs["last_update"] if "last_update" in kwargs else datetime.datetime.now()
            device.status = kwargs['status']

            conn.session.add(device)
            last_ping = cls.get_ping_status(device.id)
            if last_ping is None or last_ping.status != kwargs['status']:
                service = get_or_create(conn.session, cls, device=device, name=cls.__name__, **kwargs)
                # with conn.session.begin():
                service.last_changed = device.last_update
                service._analyze_status(**kwargs)
                conn.session.add(service)
            else:
                last_ping.last_update = device.last_update
                last_ping.response_time = kwargs['response_time']

            conn.session.commit()
        except Exception as e:
            logger.error(f'PingService | update_status | {e}')
            conn.session.rollback()
            raise

    def to_dict(self):
        ret = super().to_dict()
        ret['response_time'] = self.response_time
        return ret

    def __repr__(self):
        return f"<PingService(name='{self.name}', status='{self._status}', target_ip='{self.device.ip}')>"


class DockerService(Service):
    __tablename__ = 'docker_containers'
    id = Column(Integer, ForeignKey('services.id', ondelete='CASCADE'), primary_key=True)
    running = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    image_id = Column(String(255), nullable=True)

    service = relationship('Service', backref='docker_container_services')

    __mapper_args__ = {
        'polymorphic_identity': 'DockerService'
    }

    @property
    def container_name(self):
        return self.subname

    @container_name.setter
    def container_name(self, value):
        self.subname = value

    @classmethod
    def get_container_status(cls, device_id, container_name):
        return conn.session.query(cls).filter_by(device_id=device_id, subname=container_name).order_by(
            desc(cls.last_update)).first()

    @classmethod
    def update_status(cls, device, *args, **kwargs):
        try:
            device.last_update = kwargs["last_update"] if "last_update" in kwargs else datetime.datetime.now()
            conn.session.add(device)

            last_update = cls.get_container_status(device.id, kwargs["container_name"])
            if last_update is None or last_update.status != cls.analyze_raw_status(**kwargs):
                service = get_or_create(conn.session, cls, device=device, name=cls.__name__, **kwargs)
                # with conn.session.begin():
                service.last_changed = device.last_update
                service._analyze_status(**kwargs)
                conn.session.add(service)
            else:
                last_update.last_update = device.last_update
                for key, value in kwargs.items():
                    setattr(last_update, key, value)

            conn.session.commit()
        except Exception as e:
            logger.error(f'PingService | update_status | {e}')
            conn.session.rollback()
            raise

    @classmethod
    def analyze_raw_status(self, **kwargs):
        running = kwargs['running']
        uptime_minutes = (datetime.datetime.now() - kwargs['started_at']).total_seconds() / 60
        return running and uptime_minutes >= 6

    def _analyze_status(self, **kwargs):
        uptime_minutes = (datetime.datetime.now() - self.started_at).total_seconds() / 60
        self._set_status(self.running and uptime_minutes >= 6)

    def to_dict(self):
        ret = super().to_dict()
        ret['container_name'] = ret.pop('subname')
        ret['created_at'] = self.created_at
        ret['started_at'] = self.started_at
        ret['image_id'] = self.image_id
        return ret

    def __repr__(self):
        return f"<DockerService(name='{self.name}', status='{self._status}', container_name='{self.container_name}')>"


class DiskService(Service):
    __tablename__ = 'disk_space'
    id = Column(Integer, ForeignKey('services.id', ondelete='CASCADE'), primary_key=True)
    disk_name = Column(String(30), nullable=False)
    free_space = Column(Integer)

    service = relationship('Service', backref='disk_space_services')

    __mapper_args__ = {
        'polymorphic_identity': 'DiskService'
    }

    def to_dict(self):
        ret = super().to_dict()
        ret['disk_name'] = self.disk_name
        ret['free_space'] = self.free_space
        return ret

    def __repr__(self):
        return f"<DiskService(name='{self.name}', status='{self._status}', disk_name='{self.disk_name}', free_space='{self.free_space}')>"

# class CustomService(Service):
#     __tablename__ = 'custom_services'
#     id = Column(Integer, primary_key=True)
#     custom_property = Column(String)
#
#     def __repr__(self):
#         return f"<CustomService(name='{self.name}', status='{self.status}', custom_property='{self.custom_property}')>"
