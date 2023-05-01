import os
import time
import random
import traceback
import asyncio
import logging
import subprocess
import json
import numpy as np
import tornado.web
import tornado.httpserver
import tornado.ioloop
import tornado.websocket
import re
from queue import Queue
from copy import deepcopy
import mimetypes
from pyspimosim.protocol import Protocol, PLACEHOLDER_TIMESERIES_REPLACEMENTS, PLACEHOLDER_ARRAY_VAR_REPLACEMENTS, ProtocolEncoder
from pyspimosim.server_simulation_backend import ServerSimulationBackend


class MimeStaticFileHandler(tornado.web.StaticFileHandler):
    def get_content_type(self):
        if self.absolute_path.endswith(".js"):
            return "text/javascript"
        elif self.absolute_path.endswith(".css"):
            return "text/css"
        elif self.absolute_path.endswith(".html"):
            return "text/html"
        elif self.absolute_path.endswith(".svg"):
            return "image/svg+xml"
        elif self.absolute_path.endswith(".png"):
            return "image/png"
        elif self.absolute_path.endswith(".jpg") or self.absolute_path.endswith(".jpeg"):
            return "image/jpg"
        return mimetypes.guess_type(self.absolute_path)[0]


class ChannelHandler(tornado.websocket.WebSocketHandler):
    def initialize(self, Model, model_backend_settings):
        self.id = random.randint(0, 1e6)

        try:
            self.backend = ServerSimulationBackend(
                Model, model_backend_settings, self)
        except Exception as e:
            traceback.print_exc()

    async def on_message(self, message):
        try:
            await self.backend.enqueue_message(message)
        except Exception as e:
            traceback.print_exc()

    def on_close(self):
        try:
            self.backend.stop()
        except Exception as e:
            traceback.print_exc()
        logging.debug('>' * 28 + 'Closed-' + str(self.id) + '<' * 28)

    def open(self):
        self.set_nodelay(True)
        logging.debug('>' * 28 + 'Opened-' + str(self.id) + '<' * 28)

    def check_origin(self, origin):
        return True

    async def send_done(self, t):
        msg = json.dumps({"type": "done", "t": t})
        self.write_message(msg)

    async def send_protocol(self, msg, endian, bin_msg_charset):
        # Message format is
        # | header | buffers | JSON |
        # - JSON is encoded text excluding some "typed array" buffers
        # - Buffers are these excluded buffers concatenated together
        # - Header is big endian 32 bit unsigned ints
        #     number of buffers, bytes of buffer #0, ...
        json_msg, replacements = ProtocolEncoder.json_dumps(msg)
        buffers = replacements.array_var_buffers + replacements.timeseries_buffers

        header = len(buffers).to_bytes(4, endian)
        for b in buffers:
            header += len(b).to_bytes(4, endian)

        blocks = b''
        for b in buffers:
            blocks += b

        self.write_message(
            header + blocks + bytes(json_msg, bin_msg_charset), binary=True)

    async def send_invalid_parameter(self, invalid_parameter, invalid_parameter_msg):
        self.write_message(json.dumps({
            "type": "invalid parameter",
            "invalidParameter": invalid_parameter,
            "invalidParameterMsg": invalid_parameter_msg
        }))

    async def send_requested_objects(self, model, names):
        objects = {name: model[name] for name in names}
        msg = json.dumps({"type": "requested objects", "objects": objects})
        self.write_message(msg)

    async def send_event(self, event):
        msg = {"type": "backend event", "objects": event}
        self.write_message(msg)


class BackendConfigHandler(tornado.web.RequestHandler):
    def initialize(self, backend_settings, Model):
        self.backend_settings = backend_settings
        self.Model = Model

    async def get(self):
        host = self.backend_settings.websocket_address
        if host == "0.0.0.0":
            host = self.request.host.split(":")[0]

        self.write(f"var model = '{self.Model.name}';\n")
        self.write(
            f"var wsAddress = 'ws://{host}:{self.backend_settings.websocket_port}';\n")
        self.set_header("Content-Type", "text/javascript")


def get_listens_on_message(host, port):
    default_msg = f"Webserver listens on http://{host}:{port}"
    if host != "0.0.0.0":
        return default_msg
    try:
        own_ip = subprocess.run(
            ["hostname", "-I"], stdout=subprocess.PIPE).stdout.decode("UTF-8").split(" ")[0]
        return f"Webserver listens on http://{host}:{port}, try accessing via http://{own_ip}:{port}"
    except Exception as e:
        return default_msg


def get_pattern_for_all_files_in(dirname, index_filename="index.html"):
    pattern = "/+("
    for subdir, _, files in os.walk(dirname):
        for filename in files:
            file_path = subdir[len(dirname):].split(os.sep) + [filename]
            pattern += "|" + "/+".join(re.escape(path_part)
                                       for path_part in file_path if path_part)
            if filename == index_filename:
                pattern += "|" + "/+".join(re.escape(path_part)
                                           for path_part in file_path[:-1] if path_part) + "/*"
    return pattern + ")?"


async def start_servers(Model, backend_settings, model_backend_settings, custom_tornado_handlers=()):
    start_websocket_server(Model, backend_settings,
                           model_backend_settings, custom_tornado_handlers=())
    start_web_server(Model, backend_settings,
                     model_backend_settings, custom_tornado_handlers=())

    # Start IO/Event loop
    shutdown_event = asyncio.Event()
    await shutdown_event.wait()


def start_websocket_server(Model, backend_settings, model_backend_settings, custom_tornado_handlers=()):
    tornado.web.Application([
        ("/", ChannelHandler, dict(Model=Model,
         model_backend_settings=model_backend_settings))
    ]).listen(backend_settings.websocket_port, backend_settings.websocket_address)


def start_web_server(Model, backend_settings, model_backend_settings, custom_tornado_handlers=()):
    tornado.web.Application([
        (get_pattern_for_all_files_in(backend_settings.www_model_root), MimeStaticFileHandler, dict(
            path=backend_settings.www_model_root, default_filename="index.html")),
        ("/+backend-config.js", BackendConfigHandler,
         dict(backend_settings=backend_settings, Model=Model)),
        *Model.get_tornado_handlers(backend_settings, model_backend_settings),
        *custom_tornado_handlers,
        ("/+(.*)", MimeStaticFileHandler, dict(path=backend_settings.www_root)),
    ]).listen(backend_settings.www_port, backend_settings.www_address)
    logging.info(get_listens_on_message(
        backend_settings.www_address, backend_settings.www_port))
