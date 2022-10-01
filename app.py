import logging
import os
import socket
import sqlite3
import time
from uuid import uuid4

import redis
from flask import Flask, g, request, redirect, url_for

__version__ = 0.1
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Path to sqlite database file is passed as an environment variable
sqlite_path = os.getenv('SQLITE_PATH', ':memory:')
sqlite = sqlite3.connect(sqlite_path, check_same_thread=False)

# Redis hostname and port are passed as environment variables
r = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=os.getenv('REDIS_PORT', 6379))


@app.before_first_request
def init_db():
    sqlite.execute('''CREATE TABLE IF NOT EXISTS dume (
                        key VARCHAR(32) PRIMARY KEY, 
                        value VARCHAR(32), 
                        reqId VARCHAR(36)
                        )''')
    sqlite.commit()


@app.before_request
def initialize_request():
    g.req_start = time.time()
    g.request_id = str(uuid4())


@app.after_request
def set_response_headers(response):
    response.headers['X-App-Version'] = __version__
    response.headers['X-Request-Id'] = g.request_id
    return response


@app.teardown_request
def log_timings(exception=None):
    elapsed = time.time() - g.req_start
    app.logger.info(f'Request {g.request_id} took {elapsed} seconds to complete')


@app.route('/')
def hello_world():
    ip = socket.gethostbyname(socket.gethostname())
    port = request.environ.get('SERVER_PORT')
    return f'Hello, welcome to {ip} running on port {port}'


@app.route('/sqlite', methods=['PUT'])
def sqlite_insert():
    try:
        sqlite.execute('INSERT INTO dume VALUES (?, ?, ?)', (request.json['key'], request.json['value'], g.request_id))
        sqlite.commit()
    except sqlite3.IntegrityError:
        return 'key exists', 400
    return sqlite_select(request.json['key'])


@app.route('/sqlite/<key>', methods=['GET'])
def sqlite_select(key):
    cur = sqlite.execute('SELECT key, value, reqId FROM dume WHERE key = ?', (key,))
    result = cur.fetchall()
    if not result:
        return 'not found', 404
    return {'key': result[0][0], 'value': result[0][1], 'reqId': result[0][2]}


@app.route('/redis', methods=['PUT'])
def redis_insert():
    r.set(request.json['key'], request.json['value'])
    return redis_get(request.json['key'])


@app.route('/redis/<key>', methods=['GET'])
def redis_get(key):
    value = r.get(key)
    if not value:
        return 'not found', 404
    return {'key': key, 'value': value.decode('utf-8')}


@app.route('/health', methods=['GET'])
def health():
    return {'status': 'ok'}
