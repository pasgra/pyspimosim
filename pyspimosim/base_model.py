import sys
import os
import asyncio
from abc import ABC, abstractmethod, abstractproperty
from dataclasses import dataclass


class NoMoreDataException(Exception):
    pass


class BaseModel(ABC):
    '''
    Abstract spimosim model

    Args:
        backend:
        model_backend_settings:
        model_backend_settings: ModelBackendSettings
    '''
    multi_step = False
    save_state_after_init = True

    @classmethod
    def get_www_model_root(cls, root_dir):
        return os.path.join(root_dir, "www", cls.name)

    def __init__(self, backend, model_backend_settings, user_model_settings):
        self.backend = backend
        self.user_model_settings = user_model_settings
        self.model_backend_settings = model_backend_settings

    @abstractmethod
    def change_settings(self, model_backend_settings, restart=False):
        pass

    @abstractproperty
    def name(self):
        pass

    @classmethod
    def get_tornado_handlers(cls, backend_settings, model_backend_settings):
        return ()

    @abstractmethod
    def step(self, vars_config, t):
        pass

    def steps(self, vars_config, t, t_max, protocol, save_interval, next_send_time):
        """Calculates multiple steps (used if self.multi_step == True)"""
        pass


@dataclass
class ModelBackendSettings:
    pass
