from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from database import session, Base


class Device(Base):
    __tablename__ = 'devices'
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

    @staticmethod
    def get_group_statistics():
        groups = session.query(Device.group,
                               func.count(Device._name),
                               func.sum(func.cast(Device.status, Integer))).group_by(Device.group).all()

        return [{'name': g[0], 'count': g[1], 'online': g[2]} for g in groups]

    @staticmethod
    def get_devices_by_group():
        groups = Device.get_group_statistics()
        devices = {g['name']: session.query(Device).filter_by(group=g['name']).all() for g in groups}

        return devices
