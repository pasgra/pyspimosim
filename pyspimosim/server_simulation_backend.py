import json
import time
import asyncio
import tornado.websocket
from queue import Queue
from pyspimosim.protocol import Protocol, PLACEHOLDER_TIMESERIES_REPLACEMENTS, PLACEHOLDER_ARRAY_VAR_REPLACEMENTS
from pyspimosim.base_model import NoMoreDataException


class InvalidParameterException(Exception):
    def __init__(self, invalid_parameter, invalid_parameter_msg):
        self.invalid_parameter = invalid_parameter
        self.invalid_parameter_msg = invalid_parameter_msg


class ServerSimulationBackend():
    def __init__(self, Model, model_backend_settings, handler):
        self.model_backend_settings = model_backend_settings
        self.backend_settings = {
            'protocol': {
                'varsConfig': {},
                'saveInterval': 1
            },
            'sendInterval': 100,
            'sendFirstAfter': 20,
            'ENDIAN': 'little',
            'tMax': 0
        }
        self.bin_msg_charset = 'utf-16-le'
        self.stopped = False
        self.t = 0
        self.last_send_t = -1
        self.task = None
        self.next_send_time = 0
        self.messages = Queue()
        self.is_first_data = True
        self.invalid_parameter = None
        self.invalid_parameter_msg = None
        self.model = None
        self.Model = Model
        self.handler = handler
        self.create_protocol(0)

    def create_protocol(self, t):
        self.protocol = Protocol(
            self.backend_settings['protocol']['varsConfig'], t)

    async def next_step(self):
        if self.stopped:
            return

        try:
            if self.t < self.backend_settings['tMax']:
                await self._next_step_internal()
            else:
                if self.t != self.last_send_t:
                    await self.send_protocol()
                await self.handler.send_done(self.t)
                self.task = None
        except tornado.websocket.WebSocketClosedError as e:
            self.handler.close()
            self.pause()
        except NoMoreDataException as e:
            await self.handler.send_event({"type": "no_more_data", "t": self.t})
        except Exception as e:
            self.handler.send_error(str(e))
            self.handler.close()
            self.pause()
            raise e

    async def _next_step_internal(self):
        if self.model.multi_step:
            last_t = self.t
            self.t = await self.model.steps(
                self.backend_settings['protocol']['varsConfig'], self.t + 1, self.backend_settings['tMax'], self.protocol, self.backend_settings['protocol']['saveInterval'], self.next_send_time)
            if last_t != self.t:
                await self.send_protocol()
        else:
            self.t = self.t + 1

            await self.model.step(
                self.backend_settings['protocol']['varsConfig'], self.t)

            if self.t % self.backend_settings['protocol']['saveInterval'] == 0:
                self.protocol.set(self.t, self.model.state)

            if (self.next_send_time <= 1000 * time.time()):
                await self.send_protocol()

        self.task = asyncio.get_event_loop().create_task(self.next_step())

    def merge_backend_settings(self, new_settings):
        if not 'protocol' in new_settings:
            new_settings['protocol'] = self.backend_settings['protocol']

        if not 'varsConfig' in new_settings['protocol']:
            new_settings['protocol']['varsConfig'] = self.backend_settings['protocol']['varsConfig']

        for name in self.backend_settings['protocol']:
            if not name in new_settings['protocol']:
                new_settings['protocol'][name] = self.backend_settings['protocol'][name]

        for name in self.backend_settings:
            if not name in new_settings:
                new_settings[name] = self.backend_settings[name]

        if 'ENDIAN' in new_settings:
            if new_settings['ENDIAN'] == 'little':
                self.bin_msg_charset = 'utf-16-le'
            else:
                self.bin_msg_charset = 'utf-16-be'

        self.backend_settings = new_settings

    async def change_model_settings(self, user_model_settings, restart):
        try:
            if self.model == None or restart:
                self.model = self.Model(
                    self, self.model_backend_settings, user_model_settings)
            else:
                self.model.change_settings(user_model_settings)
            return True
        except InvalidParameterException as e:
            await self.handler.send_invalid_parameter(e.invalid_parameter, e.invalid_parameter_msg)
            if restart:
                self.invalid_parameter = e.invalid_parameter
                self.invalid_parameter_msg = e.invalid_parameter_msg
            return False

    async def restart(self, user_model_settings):
        self.pause()

        self.invalid_parameter = None

        if not (await self.change_model_settings(user_model_settings, True)):
            return

        self.is_first_data = True
        self.last_send_t = -1

        self.create_protocol(0)
        if self.model.save_state_after_init:
            self.t = 0
            self.protocol.set(self.t, self.model.state)
        else:
            self.t = -1

        await self.resume()

    async def resume(self):
        self.next_send_time = 1000 * \
            time.time() + self.backend_settings['sendFirstAfter']
        if self.task is None:
            self.task = asyncio.get_event_loop().create_task(self.next_step())

    def pause(self):
        if not self.task is None:
            self.task.cancel()
        self.task = None

    def stop(self):
        self.stopped = True
        if not self.model is None and hasattr(self.model, "stop"):
            self.model.stop()

    async def send_protocol(self):
        replace = self.protocol.get_all_transferables()
        replace_time_series = self.protocol.get_transferable_series()
        msg = {'type': 'new data', 'protocol': self.protocol, 't': self.t, 'lastSendT': self.last_send_t,
               'isFirstData': self.is_first_data, 'replace': PLACEHOLDER_ARRAY_VAR_REPLACEMENTS, 'replaceTimeSeries': PLACEHOLDER_TIMESERIES_REPLACEMENTS}

        self.is_first_data = False
        self.next_send_time += max(self.next_send_time, 1000 *
                                   time.time()) + self.backend_settings['sendInterval']
        self.last_send_t = self.t
        await self.handler.send_protocol(msg, self.backend_settings['ENDIAN'], self.bin_msg_charset)
        self.create_protocol(self.t + 1)

    async def enqueue_message(self, raw_message):
        message = json.loads(raw_message)
        if (message['command'] != 'change model settings' and self.invalid_parameter != None):
            await self.handler.send_invalid_parameter(self.invalid_parameter, self.invalid_parameter_msg)
            return

        self.messages.put(message)

        while not self.messages.empty():
            try:
                await self.process_message(self.messages.get())
            except Exception as e:
                self.handler.send_error(str(e))
                self.handler.close()
                self.pause()
                raise e

    async def process_message(self, message):
        command = message['command']
        if command == 'change backend settings':
            self.merge_backend_settings(message['settings'])

            if (message['resume']):
                await self.resume()
        elif command == 'change model settings':
            if message['restart']:
                await self.restart(message['modelSettings'])
            else:
                await self.change_model_settings(message['modelSettings'], False)
        elif command == 'request objects':
            await self.handler.send_requested_objects(self.model, message['names'])
        elif command == 'resume':
            await self.resume()
        elif command == 'pause':
            self.pause()
        else:
            raise Exception('Cannot understand message: ' + message)
