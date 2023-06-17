import services.webhook
from flask import render_template, jsonify, request
import database as db
import datetime


def add_app_routes(app):
    @app.route('/')
    def index():
        groups = db.Device.get_group_statistics()
        return render_template('summary.html', groups=groups)

    @app.route('/device/<device_id>')
    def device(device_id):
        device = db.Device.query.get(device_id).to_dict(full_details=True)
        return render_template('device.html', device=device)

    @app.route('/device/<device_id>/info')
    def device_info(device_id):
        device = db.Device.query.get(device_id).to_dict(full_details=True)
        return render_template('device_info.html', device=device)

    # API
    @app.route('/api/all')
    def api_ping_status():
        now = datetime.datetime.now()
        groups = db.Device.get_group_statistics()
        diff_ms = (datetime.datetime.now() - now).total_seconds()
        now = datetime.datetime.now()
        # db.logger.info(f'groups statistics {diff_ms}')
        devices = db.Device.get_devices_by_group()
        diff_ms = (datetime.datetime.now() - now).total_seconds()
        now = datetime.datetime.now()
        # db.logger.info(f'devices by group {diff_ms}')
        device_services = db.Device.get_services_statistics()
        diff_ms = (datetime.datetime.now() - now).total_seconds()
        now = datetime.datetime.now()
        # db.logger.info(f'services statistics {diff_ms}')

        return jsonify({'groups': groups, 'devices': devices, 'services': device_services})

    @app.route('/api/device/<device_id>', methods=['GET'])
    def api_device(device_id):
        device = db.Device.query.get(device_id)
        return jsonify(device.to_dict(full_details=True))

    @app.route('/webhook/containers', methods=['POST'])
    def receive_data():
        data = request.json
        ip_address = request.remote_addr

        ok = services.webhook.handle_webhook_data(data, ip_address)

        if ok:
            return jsonify({'ok': True, 'info': 'handled correctly'}), 200
        else:
            return jsonify({'ok': False, 'info': 'not handled correctly'}), 400
