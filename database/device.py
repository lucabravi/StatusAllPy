import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, case, and_

from database import conn, Base, logger
from .services import Service


class Device(Base):
    __tablename__ = 'devices'
    id = Column(Integer, primary_key=True)
    ip = Column(String(15), nullable=True, unique=True)
    _name = Column(String(30), nullable=False, unique=True)
    group = Column(String(30), nullable=False, default='client')
    status = Column(Boolean, nullable=False, default=False)
    last_update = Column(DateTime, nullable=True)
    last_changed = Column(DateTime, nullable=True)

    @property
    def name(self):
        if self._name:
            return f'{".".join(self.ip.split(".")[-2:]) + " " if self.ip.startswith("192.168") else ""}{self._name}'
        else:
            return self.ip

    @name.setter
    def name(self, value):
        self._name = value

    @staticmethod
    def get_group_statistics():
        # query = text('''
        #     SELECT d."group", count(1), sum(case when s.status = 1 then 1 else 0 end)
        #     FROM devices d
        #     LEFT JOIN (
        #         SELECT s.*
        #         FROM services s
        #         INNER JOIN (
        #             SELECT device_id, MAX(last_update) AS max_last_update
        #             FROM services
        #             GROUP BY device_id
        #         ) subquery ON s.device_id = subquery.device_id AND s.last_update = subquery.max_last_update
        #     ) s ON d.id = s.device_id
        #     GROUP BY d."group"
        # ''')
        # res = conn..execute(query)
        res = conn.session.query(
            Device.group,
            func.count(Device.id),
            func.sum(case((Device.status == 1, 1), else_=0
                          )
                     )
        ).group_by(Device.group)

        groups = [{'name': group, 'count': device_count, 'online': ping_service_count}
                  for group, device_count, ping_service_count in res.all()]

        return groups

    @staticmethod
    def get_services_statistics():
        subquery = (
            conn.session.query(
                Service.device_id.label('device_id'),
                Service.name.label('name'),
                Service.subname.label('subname'),
                func.max(Service.last_update).label('max_last_update')
            )
            .join(Device, Device.id == Service.device_id)
            .group_by(Device.id, Service.name, Service.subname)
            .subquery()
        )

        services = (
            conn.session.query(
                Service
            )
            .join(subquery, and_(
                Service.name == subquery.c.name,
                # Service.subname == subquery.c.subname,
                Service.last_update == subquery.c.max_last_update,
                Service.device_id == subquery.c.device_id,
                subquery.c.name != 'PingService'
            ))
            .group_by(Service.id, Service.device_id, Service.name, Service.subname)
        ).all()

        groups = conn.session.query(Device.group).distinct()
        services_dict = {
            g[0]: {service.device_id: [] for service in services if service.device.group == g[0]}
            for g in groups
        }

        for service in services:
            services_dict[service.device.group][service.device_id].append(service.to_dict())

        return services_dict

    @classmethod
    def get_devices_by_group(cls, with_services=False):
        groups = conn.session.query(Device.group).distinct()
        devices = {g[0]: {d.id: d.to_dict() for d in conn.session.query(Device).filter_by(group=g[0])} for g in groups}

        # devices = {
        #     g[0]: {
        #         device.id: {
        #             'info': device.to_dict()
        #         }
        #         for device in conn.session.query(Device).filter_by(group=g[0])}
        #     for g in groups
        # }
        # services = cls.get_services_statistics().all()
        # for service in services:
        #     if 'services' not in devices[service.device.group][service.device_id]:
        #         devices[service.device.group][service.device_id]['services'] = []
        #     devices[service.device.group][service.device_id]['services'].append(service.to_dict())

        return devices

    def to_dict(self, full_details=False):
        ret = {
            'id': self.id,
            'ip': self.ip,
            'name': self.name,
            'group': self.group,
            'last_update': self.last_update,
            'last_changed': self.last_changed,
            'status': self.status,
        }
        if full_details:
            temp = Service.get_services_by_device(device_id=self.id)
            services = [x.to_dict() for x in temp]
            ret['services'] = services

        return ret

        # return {c.name: getattr(self, c.name) for c in self.__table__.columns} | {'name': self.name}
