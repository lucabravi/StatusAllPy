import distutils
import os
from distutils.util import strtobool

import database
from . import *
from utils import network

curr_host_ips: list[str] = network.get_ip_addresses()
curr_host_device: database.Device | None = database.conn.session.query(database.Device).filter_by(ip=os.getenv('HOST_WEBHOOK_IP'), group='SERVER').first() \
    if os.getenv('HOST_WEBHOOK_IP', None) is not None \
    else None
curr_host_checked: bool = False


def handle_webhook_data(data, ip_address):
    if 'containers' in data:
        return handle_container_data(data, ip_address)


def handle_container_data(data, ip_address):
    try:
        global curr_host_ips, curr_host_device, curr_host_checked
        containers = data['containers']

        for container in containers:
            container_name = container['name']
            image_id = container['image_id']
            started_at = container['started_at']
            started_at = datetime.datetime.strptime(started_at[:19], "%Y-%m-%dT%H:%M:%S")

            running = bool(strtobool(container['running']))
            created_at = container['created_at']
            created_at = datetime.datetime.strptime(created_at[:19], "%Y-%m-%dT%H:%M:%S")

            if curr_host_device is not None and curr_host_device.ip == ip_address:
                device = curr_host_device
            else:
                device = database.conn.session.query(database.Device).filter_by(ip=ip_address, group='SERVER').first()
                if device is None and not curr_host_checked:
                    if ip_address in curr_host_ips:
                        check_curr_host = [database.conn.session.query(database.Device)
                                           .filter_by(ip=x, group='SERVER')
                                           .first() for x in curr_host_ips]
                        check_curr_host = [x for x in check_curr_host if x is not None]
                        if len(check_curr_host) > 0:
                            curr_host_device = check_curr_host[0]
                            curr_host_checked = True
                        else:
                            raise Exception(f'Received webhook container data from unkwnown device {ip_address}')
                    else:
                        raise Exception(f'Received webhook container data from unkwnown device {ip_address}')

            database.services.DockerService.update_status(
                device=device,
                container_name=container_name,
                image_id=image_id,
                running=running,
                started_at=started_at,
                created_at=created_at
            )

        return True

    except Exception as e:
        logger.error(f'handle_container_data: {e}')
        return False
