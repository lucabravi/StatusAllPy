import logging
import threading
import asyncio
import os
from flask import Flask, render_template
import database as db

from services import ping

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)
app = Flask(__name__)


@app.route('/')
def index():
    groups = db.Device.get_group_statistics()
    devices = db.Device.get_devices_by_group()
    return render_template('index.html', groups=groups, devices=devices)


if __name__ == '__main__':
    db.init_db()

    use_reloader = True
    if not use_reloader or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        logger.info('Starting service thread : ping')
        loop = asyncio.new_event_loop()
        loop.create_task(ping.start_ping_checks())
        thread = threading.Thread(target=loop.run_forever)
        thread.start()

    logger.info('run app')
    app.run(host='127.0.0.1', debug=True, port=5000, use_reloader=use_reloader)
