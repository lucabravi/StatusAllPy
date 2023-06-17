from . import *


def handle_webhook_data(data, ip_address):
    if 'containers' in data:
        return handle_container_data(data, ip_address)


def handle_container_data(data, ip_address):
    try:
        containers = data['containers']

        for container in containers:
            container_name = container['name']
            image_id = container['image_id']
            started_at = container['started_at']
            started_at = datetime.datetime.strptime(started_at[:19], "%Y-%m-%dT%H:%M:%S")

            created_at = container['created_at']
            created_at = datetime.datetime.strptime(created_at[:19], "%Y-%m-%dT%H:%M:%S")

            device = database.get_or_create(database.conn.session, database.Device, ip=ip_address, group='SERVER')
            database.services.DockerService.update_status(
                device=device,
                container_name=container_name,
                image_id=image_id,
                started_at=started_at,
                created_at=created_at
            )

        return True

    except Exception as e:
        logger.error(f'handle_container_data: {e}')
        return False
