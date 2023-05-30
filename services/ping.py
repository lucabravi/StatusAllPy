import asyncio
import os

from . import *
from database import get_or_create, PingService


# from pythonping import ping


async def ping_device(device):
    # while True:
    try:
        if platform.system() == 'Windows':
            process = await asyncio.create_subprocess_exec('ping', '-n', '1', device.ip, stdout=PIPE, stderr=PIPE,
                                                           text=False)
        else:
            process = await asyncio.create_subprocess_exec('ping', '-c', '1', '-W', '0.3', device.ip,
                                                           stdout=PIPE, stderr=PIPE, text=False)
        stdout, stderr = await process.communicate()
        ping_ms = extract_ping_time(str(stdout))
        status = process.returncode == 0
        # ping_status = ping(device.ip, count=1, timeout=0.3, verbose=False)
        # print(ping_status)

        now = datetime.datetime.now()
        # device = Device.query.get(device.id)
        PingService.update_status(device=device, status=status, response_time=ping_ms)

        if status:
            logger.info(f"{device.name}: {status}")
        else:
            logger.info(f"{device.name}: {status}")

    except Exception as e:
        logger.error(e)

        # finally:
        #     await asyncio.sleep(30)


def extract_ping_time(data_string) -> int:
    start_marker = ", time "
    end_marker = "ms"

    try:
        start_index = data_string.index(start_marker) + len(start_marker)
        end_index = data_string.index(end_marker, start_index)
        ping_time = data_string[start_index:end_index]
        return int(ping_time)
    except ValueError:
        return -1


# async def start_ping_checks():
#     devices = conn.session.query(Device).order_by(Device.id).all()
#
#     tasks = []
#     for device in devices:
#         task = asyncio.create_task(ping_device(device))
#         tasks.append(task)
#         asyncio.sleep(0.2)
#
#     await asyncio.gather(*tasks)

############ V2


async def worker(queue):
    while True:
        funct, param = await queue.get()
        await funct(param)
        await asyncio.sleep(0.3)
        await queue.put((funct, param))


queue = asyncio.Queue()


async def start_ping_checks():
    num_workers = os.cpu_count()
    logger.info(f'CPU num: {num_workers} | starting {num_workers} ping workers')
    workers = [asyncio.create_task(worker(queue)) for _ in range(num_workers)]

    devices = database.conn.session.query(database.Device).order_by(database.Device.id).all()

    for device in devices:
        await queue.put((ping_device, device))

    # Attendi il completamento di tutti i job
    await queue.join()

    # Ferma i worker
    for worker_task in workers:
        worker_task.cancel()
