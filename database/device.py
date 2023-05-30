import json

from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, case, select, text, and_
from sqlalchemy.orm import aliased

from database import conn, Base, query_to_dict
from .services import Service, PingService, DockerContainer, DiskSpace

import datetime


class Device(Base):
    __tablename__ = 'devices'
    id = Column(Integer, primary_key=True)
    ip = Column(String, nullable=False, unique=True)
    _name = Column(String, nullable=False, unique=True)
    group = Column(String, nullable=False, default='client')
    status = Column(Boolean, nullable=False, default=False)
    last_update = Column(DateTime, nullable=True)

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
        # res = conn.session.execute(query)
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
                func.max(Service.last_update).label('max_last_update')
            )
            .join(Device, Device.id == Service.device_id)
            .group_by(Device.id, Service.name)
            .subquery()
        )

        query = (
            conn.session.query(
                Service.device_id,
                Service.name,
                Service.status,
                Service.last_update,
                Service.last_changed
            )
            .join(subquery, and_(
                Service.name == subquery.c.name,
                Service.last_update == subquery.c.max_last_update,
                Service.device_id == subquery.c.device_id,
                subquery.c.name != 'PingService'
            ))
            .group_by(Service.device_id, Service.name)
        )

        results = query_to_dict(query, key='device_id')
        return results

        # json_results = {}
        #
        # # Iterazione sui risultati per trasformarli in dizionari
        # for result in results:
        #     json_results[result.device_id] = {
        #         'name': result.name,
        #         'status': result.status,
        #         'last_update': result.last_update.strftime('%Y-%m-%d %H:%M:%S'),  # Conversione del datetime in stringa
        #         'last_changed': result.last_changed.strftime('%Y-%m-%d %H:%M:%S')
        #     }
        #
        # return json_results

    @staticmethod
    def get_devices_by_group():
        groups = conn.session.query(Device.group).distinct()
        devices = {g[0]: [d.to_dict() for d in conn.session.query(Device).filter_by(group=g[0])] for g in groups}
        return devices

    def to_dict(self, full_details=False):
        ret = {
            'ip': self.ip,
            'name': self.name,
            'group': self.group,
            'last_update': self.last_update,
            'status': self.status,
        }
        if full_details:
            device_services = [x.to_dict() for x in Service.get_services_by_device(device_id=self.id)]
            ret['services'] = device_services

        return ret

        # return {c.name: getattr(self, c.name) for c in self.__table__.columns} | {'name': self.name}
