import datetime
import platform
import asyncio
from subprocess import PIPE
import logging
from database import session
from database.device import Device

logger = logging.getLogger(__name__)


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

    devices = session.query(Device).order_by(Device.id).all()

    tasks = []
    for device in devices:
        task = asyncio.create_task(ping_device(device))
        tasks.append(task)

    await asyncio.gather(*tasks)
