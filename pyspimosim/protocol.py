import numpy as np
from enum import Enum, auto
import json
from copy import deepcopy


class ProtocolVarTransferMode:
    TIME_STEP_WISE = auto()
    ALL_AT_ONCE = auto()


NUMBER_TYPES = {
    'Int8': np.int8,
    'Uint8': np.uint8,
    'Int16': np.int16,
    'Uint16': np.uint16,
    'Int32': np.int32,
    'Uint32': np.uint32,
    'Int64': np.int64,
    'Uint64': np.uint64,
    'Float32': np.float32,
    'Float64': np.float64
}


ARRAY_TYPES = {name + 'Array': np_type for name,
               np_type in NUMBER_TYPES.items()}


class ProtocolVar:
    def __init__(self, name, t_min=0):
        self.name = name
        self.t_min = t_min
        self.t_max = t_min - 1
        self.data = []

    def copy_val(self, val):
        return deepcopy(val)

    def copy_vals(self, vals):
        return deepcopy(vals)

    def set(self, t, val):
        if self.t_max + 1 == t:
            # append
            self.data.append(self.copy_val(val))
            self.t_max = t
        elif self.t_max < t:
            # pad and append
            self.data.extend([None] * (t - self.t_max))
            self.data[t - self.t_min] = self.copy_val(val)
            self.t_max = t
        else:
            # replace
            seld.data[t - self.tmin] = self.copy_val(val)

    def set_all(self, t, vals):
        t_last = t + len(vals) - 1
        if self.t_max + 1 == t:
            # append
            self.data.extend(self.copy_vals(vals))
            self.t_max = t_last
        elif self.t_max + 1 < t:
            # pad and append
            self.data.extend([None] * (t - self.t_max) + self.copy_vals(vals))
            self.t_max = t_last
        elif self.t_max < t_last:
            # pad and replace
            self.data.extend([None] * (t - t_last))
            self.data[t - self.t_min:] = self.copy_vals(vals)
            self.t_max = t_last
        else:
            # replace
            self.data[t - self.t_min:t_last -
                      self.t_min + 1] = self.copy_vals(vals)

    def as_dict(self):
        return {
            "tMin": self.t_min,
            "tMax": self.t_max,
            "data": self.data
        }

    def get_transfer_mode(self):
        return ProtocolVarTransferMode.TIME_STEP_WISE

    def get_transferable(self, t):
        return None

    def get_all_transferables(self):
        return [self.get_transferable(t) for t in range(self.t_min, self.t_max + 1)]

    def get_transferable_series(self):
        return None


class NPProtocolVar(ProtocolVar):
    def __init__(self, name, t_min, dtype=np.float64):
        self.name = name
        self.t_min = t_min
        self.t_max = t_min - 1
        self.data = np.array([], dtype=dtype)
        self.dtype = dtype

    def set(self, t, val):
        if self.t_max + 1 == t:
            self.data = np.append(self.data, np.array(val, dtype=self.dtype))
            self.t_max = t
        elif self.t_max < t:
            padding = np.full(t - self.t_max, np.NaN, dtype=self.dtype)
            self.data = np.append(self.data, padding, axis=0)
            self.data[t - self.t_min] = val
            self.t_max = t
        else:
            self.data[t - self.t_min] = val

    def set_all(self, t, vals):
        t_last = t + len(vals) - 1
        if self.t_max + 1 == t:
            # append
            self.data = np.append(self.data, vals, axis=0)
            self.t_max = t_last
        elif self.t_max + 1 < t:
            # pad and append
            padding = np.full(t - self.t_max - 1, np.NaN, dtype=self.dtype)
            self.data = np.append(
                np.append(self.data, padding, axis=0), vals, axis=0)
            self.t_max = t_last
        elif self.t_max < t_last:
            # pad and replace
            padding = np.full(t_last - self.t_max, np.NaN, dtype=self.dtype)
            self.data = np.append(self.data, padding, axis=0)
            self.data[t - self.t_min:] = vals
            self.t_max = t_last
        else:
            # replace
            self.data[t - self.t_min:t_last - self.t_min + 1] = vals

    def as_dict(self):
        return {
            "tMin": self.t_min,
            "tMax": self.t_max,
            "data": {}
        }

    def get_transfer_mode(self):
        return ProtocolVarTransferMode.ALL_AT_ONCE

    def get_transferable(self, t):
        return None

    def get_transferable_series(self):
        return self.data


class NPArrayProtocolVar(ProtocolVar):
    def __init__(self, name, t_min, dtype=np.float64):
        super().__init__(name, t_min)
        self.dtype = dtype

    def as_dict(self):
        return {
            "tMin": self.t_min,
            "tMax": self.t_max,
            "data": {}
        }

    def copy_val(self, val):
        return np.array(val, dtype=self.dtype, copy=True)

    def copy_vals(self, vals):
        return [np.array(val, dtype=self.dtype, copy=True) for val in vals]

    def get_transfer_mode(self):
        return ProtocolVarTransferMode.TIME_STEP_WISE

    def get_transferable(self, t):
        return self.data[t - self.t_min]

    def get_all_transferables(self):
        return self.data

    def get_transferable_series(self):
        return None


class SpinArrayProtocolVar(NPArrayProtocolVar):
    def get_transferable(self, t):
        return len(spin_var).to_bytes(4, self.backend_settings['ENDIAN']) + np.packbits(spin_var + 1).tobytes()


class Placeholder:
    pass


PLACEHOLDER_ARRAY_VAR_REPLACEMENTS = Placeholder()
PLACEHOLDER_TIMESERIES_REPLACEMENTS = Placeholder()


class Protocol:
    def __init__(self, vars_config, t_min):
        self.vars = {}
        self.t_min = t_min
        self.t_max = t_min - 1
        self.update_vars(vars_config)

    def update_vars(self, vars_config):
        for name in self.vars:
            if not name in vars_config:
                del self.vars[name]

        for name, value in vars_config.items():
            self._update_var(name, value)

    def _update_var(self, name, value):
        if value['type'] in ARRAY_TYPES.keys():
            self.vars[name] = NPArrayProtocolVar(
                name, self.t_min, dtype=ARRAY_TYPES[value['type']])
        elif value['type'] in NUMBER_TYPES.keys():
            self.vars[name] = NPProtocolVar(
                name, self.t_min, dtype=NUMBER_TYPES[value['type']])
        elif value['type'] == 'SpinArray':
            self.vars[name] = SpinArrayProtocolVar(
                name, self.t_min, dtype=NUMBER_TYPES[value['type']])
        else:
            self.vars[name] = ProtocolVar(name, self.t_min)

    def set(self, t, state):
        self.t_max = max(self.t_max, t)
        for name, pvar in self.vars.items():
            pvar.set(t, state[name])

    def as_dict(self):
        return {
            "tMin": self.t_min,
            "tMax": self.t_max,
            "vars": self.vars
        }

    def get_all_transferables(self):
        transferables = []
        for pvar in self.vars.values():
            if pvar.get_transfer_mode() == ProtocolVarTransferMode.TIME_STEP_WISE:
                transferables.extend(pvar.get_all_transferables())
        return transferables

    def get_transferable_series(self):
        transferables = []
        for pvar in self.vars.values():
            if pvar.get_transfer_mode() == ProtocolVarTransferMode.TIME_STEP_WISE:
                transferables.append(pvar.get_transferable_series())
        return transferables


class ProtocolEncoderReplacements:
    def __init__(self):
        self.array_var_buffers = []
        self.array_var_names = []
        self.timeseries_buffers = []
        self.timeseries_names = []


class ProtocolEncoder(json.JSONEncoder):
    def __init__(self, replacements, **kw):
        self.replacements = replacements
        json.JSONEncoder.__init__(self, **kw)

    @staticmethod
    def json_dumps(obj):
        # bind replacements object to class using closure
        replacements = ProtocolEncoderReplacements()

        class BoundEncoder(ProtocolEncoder):
            def __init__(self, **kwargs):
                super().__init__(replacements=replacements, **kwargs)

        json_msg = json.dumps(obj, cls=BoundEncoder)
        return json_msg, replacements

    def default(self, obj):
        if obj is PLACEHOLDER_ARRAY_VAR_REPLACEMENTS:
            return self.replacements.array_var_names

        if obj is PLACEHOLDER_TIMESERIES_REPLACEMENTS:
            return self.replacements.timeseries_names

        if isinstance(obj, np.ndarray):
            self.buffers.append(obj.tobytes())
            return

        if isinstance(obj, Protocol):
            return obj.as_dict()

        if isinstance(obj, ProtocolVar) and obj.get_transfer_mode() == ProtocolVarTransferMode.ALL_AT_ONCE:
            self.replacements.timeseries_buffers.append(
                obj.get_transferable_series().tobytes())
            self.replacements.timeseries_names.append(obj.name)
            return obj.as_dict()

        if isinstance(obj, ProtocolVar) and obj.get_transfer_mode() == ProtocolVarTransferMode.TIME_STEP_WISE:
            for b in obj.get_all_transferables():
                self.replacements.array_var_buffers.append(b.tobytes())
            self.replacements.array_var_names.append(obj.name)
            return obj.as_dict()

        return json.JSONEncoder.default(self, obj)
