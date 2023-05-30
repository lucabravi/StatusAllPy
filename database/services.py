import datetime
from operator import and_

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Index, desc, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from . import conn, Base, get_or_create


class Service(Base):
    __tablename__ = 'services'

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id'))
    name = Column(String)
    status = Column(Boolean)
    last_update = Column(DateTime, nullable=False, default=datetime.datetime.now)
    last_changed = Column(DateTime, nullable=False, default=datetime.datetime.now)

    device = relationship('Device', backref='services')

    indice_servizi = Index(device_id, last_update)

    def __repr__(self):
        return f"<Service(name='{self.name}', status='{self.status}')>"

    def _analyze_status(self, **kwargs):
        self._set_status(kwargs['status'])

    def _set_status(self, status):
        self.last_update = datetime.datetime.now()
        if status != self.status:
            self.last_changed = datetime.datetime.now()
            self.status = status

    @classmethod
    def update_status(cls, device, *args, **kwargs):
        device.last_update = kwargs["last_update"] if "last_udpate" in kwargs else datetime.datetime.now()
        if cls.__name__ == PingService.__name__:
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
    #         .filter_by(device_id=device_id)\
    #         .group_by(cls.name)\
    #         .all()

    @classmethod
    def get_services_by_device(cls, device_id):

        subquery = (
            conn.session.query(Service.name, func.max(Service.last_update).label('max_last_update'))
            .filter(Service.device_id == device_id)
            .group_by(Service.name)
            .subquery()
        )

        result = conn.session.query(Service) \
            .join(subquery, and_(Service.name == subquery.c.name, Service.last_update == subquery.c.max_last_update)) \
            .filter(Service.device_id == device_id)

        return result.all()

    def to_dict(self):
        return {
            'name': self.name,
            'status': self.status,
            'last_update': self.last_update,
            'last_changed': self.last_changed
        }


class PingService(Service):
    __tablename__ = 'ping_services'
    id = Column(Integer, ForeignKey('services.id'), primary_key=True)
    response_time = Column(Integer, default=-1, nullable=False)

    def __repr__(self):
        return f"<PingService(name='{self.name}', status='{self.status}', target_ip='{self.target_ip}')>"


class DockerContainer(Service):
    __tablename__ = 'docker_containers'
    id = Column(Integer, ForeignKey('services.id'), primary_key=True)
    container_name = Column(String)
    created_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    image_id = Column(String)

    service = relationship('Service', backref='docker_container_services')

    def _analyze_status(self, **kwargs):
        uptime_minutes = (datetime.datetime.now() - self.started_at).total_seconds() / 60
        self._set_status(uptime_minutes >= 5)

    def __repr__(self):
        return f"<DockerContainer(name='{self.name}', status='{self.status}', container_name='{self.container_name}')>"


class DiskSpace(Service):
    __tablename__ = 'disk_space'
    id = Column(Integer, ForeignKey('services.id'), primary_key=True)
    disk_name = Column(String)
    free_space = Column(Integer)

    service = relationship('Service', backref='disk_space_services')

    def __repr__(self):
        return f"<DiskSpace(name='{self.name}', status='{self.status}', disk_name='{self.disk_name}', free_space='{self.free_space}')>"

# class CustomService(Service):
#     __tablename__ = 'custom_services'
#     id = Column(Integer, primary_key=True)
#     custom_property = Column(String)
#
#     def __repr__(self):
#         return f"<CustomService(name='{self.name}', status='{self.status}', custom_property='{self.custom_property}')>"
