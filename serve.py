import sys
import socket
import logging
from waitress import serve
from app import App


def serve_to_lan():
    host = '0.0.0.0'    # Ubunut WSL would bind to localhost
    port = 5000         # Can not bind to socket below 1024 on Unix without sudo
    if sys.platform == 'win32':
        host = socket.gethostbyname(socket.gethostname())   
        port = 80

    logging.info('Serving at %s', host)
    serve(App, host=host, port=port)


if __name__ == '__main__':
    serve_to_lan()
