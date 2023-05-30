import services.webhook
from flask import render_template, jsonify, request
import database as db


def add_app_routes(app):
    @app.route('/')
    def index():
        groups = db.Device.get_group_statistics()
        devices = db.Device.get_devices_by_group()
        return render_template('index.html', groups=groups, devices=devices)

    @app.route('/beta')
    def beta():
        groups = db.Device.get_group_statistics()
        return render_template('index_dyn.html', groups=groups)

    @app.route('/webhook/containers', methods=['POST'])
    def receive_data():
        data = request.json
        ip_address = request.remote_addr

        ok = services.webhook.handle_webhook_data(data, ip_address)

        if ok:
            return jsonify({'ok': True, 'info': 'handled correctly'}), 200
        else:
            return jsonify({'ok': False, 'info': 'not handled correctly'}), 400

    # API
    @app.route('/api/ping_status')
    def api_ping_status():
        groups = db.Device.get_group_statistics()
        devices = db.Device.get_devices_by_group()
        device_services = db.Device.get_services_statistics()

        return jsonify({'groups': groups, 'devices': devices, 'device_services': device_services})
