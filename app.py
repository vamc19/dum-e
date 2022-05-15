import logging
import socket
import time
from uuid import uuid4

from flask import Flask, g, request

__version__ = 0.1
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


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


@app.route('/health', methods=['GET'])
def health():
    return {'status': 'ok'}
