import datetime
from operator import and_

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Index, desc, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, selectin_polymorphic, with_polymorphic

from . import conn, Base, get_or_create


class Service(Base):
    __tablename__ = 'services'

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id'))
    name = Column(String)
    subname = Column(String)
    _status = Column(Boolean)
    last_update = Column(DateTime, nullable=False, default=datetime.datetime.now)
    last_changed = Column(DateTime, nullable=False, default=datetime.datetime.now)

    device = relationship('Device', backref='services')
    indice_servizi = Index(device_id, last_update)

    __mapper_args__ = {
        'polymorphic_identity': 'service',
        "with_polymorphic": "*",
        'polymorphic_on': name,
    }

    def __repr__(self):
        return f"<Service(name='{self.name}', status='{self._status}')>"

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
        device.last_update = kwargs["last_update"] if "last_udpate" in kwargs else datetime.datetime.now()
        if cls.__name__ == PingService.__name__:
            if device.last_changed is None or device.status != kwargs['status']:
                device.last_changed = datetime.datetime.now()
            device.status = kwargs['status']

        service = get_or_create(conn.session, cls, device=device, name=cls.__name__, **kwargs)
        service._analyze_status(**kwargs)
        conn.session.add(device)
        conn.session.commit()

    @classmethod
    def get_ping_status(cls, device_ip):
        return conn.session.query(cls).filter_by(device_id=device_ip).order_by(desc(cls.last_update)).first()

    # get_services_by_device(self.id)
    # @classmethod
    # def get_services_by_device(cls, device_id):
    #     return conn.session.query(cls)\
    #         .filter_by(device_id=device_id)\identifier.sqlite
    #         .group_by(cls.name)\
    #         .all()

    @classmethod
    def get_services_by_device(cls, device_id):
        all_kind_services = with_polymorphic(Service, [PingService, DockerContainer])

        subquery = (
            conn.session.query(Service.name, Service.subname, func.max(Service.last_update).label('max_last_update'))
            .filter(Service.device_id == device_id)
            .group_by(Service.name, Service.subname)
            .subquery()
        )

        result = conn.session.query(all_kind_services) \
            .join(subquery, and_(Service.name == subquery.c.name, Service.last_update == subquery.c.max_last_update)) \
            .filter(Service.device_id == device_id)

        return result

    def to_dict(self):
        return {
            'name': self.name,
            'subname': self.subname,
            'status': self._status,
            'last_update': self.last_update,
            'last_changed': self.last_changed
        }


class PingService(Service):
    __tablename__ = 'ping_services'
    id = Column(Integer, ForeignKey('services.id'), primary_key=True)
    response_time = Column(Integer, default=-1, nullable=False)

    __mapper_args__ = {
        "polymorphic_load": "inline",
        'polymorphic_identity': 'PingService'
    }

    def __repr__(self):
        return f"<PingService(name='{self.name}', status='{self._status}', target_ip='{self.target_ip}')>"

    def to_dict(self):
        ret = super().to_dict()
        ret['response_time'] = self.response_time
        return ret


class DockerContainer(Service):
    __tablename__ = 'docker_containers'
    id = Column(Integer, ForeignKey('services.id'), primary_key=True)
    created_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    image_id = Column(String)

    service = relationship('Service', backref='docker_container_services')

    __mapper_args__ = {
        'polymorphic_identity': 'DockerContainer'
    }

    @property
    def container_name(self):
        return self.subname

    @container_name.setter
    def container_name(self, value):
        self.subname = value

    def _analyze_status(self, **kwargs):
        uptime_minutes = (datetime.datetime.now() - self.started_at).total_seconds() / 60
        self._set_status(uptime_minutes >= 5)

    def __repr__(self):
        return f"<DockerContainer(name='{self.name}', status='{self._status}', container_name='{self.container_name}')>"

    def to_dict(self):
        ret = super().to_dict()
        ret['container_name'] = ret.pop('subname')
        ret['created_at'] = self.created_at
        ret['started_at'] = self.started_at
        ret['image_id'] = self.image_id
        return ret


class DiskSpace(Service):
    __tablename__ = 'disk_space'
    id = Column(Integer, ForeignKey('services.id'), primary_key=True)
    disk_name = Column(String)
    free_space = Column(Integer)

    service = relationship('Service', backref='disk_space_services')

    __mapper_args__ = {
        'polymorphic_identity': 'DiskSpace'
    }

    def __repr__(self):
        return f"<DiskSpace(name='{self.name}', status='{self._status}', disk_name='{self.disk_name}', free_space='{self.free_space}')>"

    def to_dict(self):
        ret = super().to_dict()
        ret['disk_name'] = self.disk_name
        ret['free_space'] = self.free_space
        return ret

# class CustomService(Service):
#     __tablename__ = 'custom_services'
#     id = Column(Integer, primary_key=True)
#     custom_property = Column(String)
#
#     def __repr__(self):
#         return f"<CustomService(name='{self.name}', status='{self.status}', custom_property='{self.custom_property}')>"
