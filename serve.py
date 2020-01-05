import socket
import logging
from waitress import serve
from app import App


def serve_to_lan():
    host = socket.gethostbyname(socket.gethostname())
    logging.info('Serving at %s', host)
    serve(App, host=host, port=80)


if __name__ == '__main__':
    serve_to_lan()