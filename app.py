import os
import sys
import logging
import threading
import asyncio

from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

import database as db
from services import ping

TEST = True
use_reloader = TEST

cur_dir = os.path.dirname(os.path.realpath(__file__))
os.chdir(cur_dir)
sys.path.append(cur_dir)

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.WARNING)
logger = logging.getLogger(__name__)
app = Flask(__name__, static_folder='static',)

scheduler = BackgroundScheduler()


def initialize_scheduler():
    def clean_old_records():
        with app.app_context():
            db.delete_old_records()

    clean_old_records()

    logger.info('Starting apscheduler to logrotate db periodically')
    scheduler.add_job(clean_old_records, 'interval', minutes=30)
    scheduler.start()


def init_app(app):
    with app.app_context():
        from database import init_db
        init_db(app=app, echo=False)
        from routes import add_app_routes
        add_app_routes(app)

    if not use_reloader or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        logger.info('Starting service thread : ping')

        loop = asyncio.new_event_loop()
        with app.app_context():
            # asyncio.run(ping.start_ping_checks())
            loop.create_task(ping.start_ping_checks())
        thread = threading.Thread(target=loop.run_forever)
        thread.start()

        initialize_scheduler()


if __name__ == 'app':
    init_app(app)

if __name__ == '__main__':
    init_app(app)

    logger.info('run app')
    app.run(host='0.0.0.0', debug=TEST, port=5000, use_reloader=use_reloader)
