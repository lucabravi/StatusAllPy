from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import session, Base


class Container(Base):
    __tablename__ = 'containers'
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
