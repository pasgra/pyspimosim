#!/usr/bin/env python3

# This script supports autocompletion with argcomplete: PYTHON_ARGCOMPLETE_OK

import random
import numpy as np
from pyspimosim.base_model import BaseModel, ModelBackendSettings
from pyspimosim.main import model_main


class Model(BaseModel):
    name = "ising"

    def __init__(self, backend, model_backend_settings, user_model_settings):
        super().__init__(backend, model_backend_settings, user_model_settings)
        self.state = {}
        self.change_settings(user_model_settings)

    def change_settings(self, user_model_settings, restart=False):
        self.j = user_model_settings['parameters']['j']
        self.beta = user_model_settings['parameters']['beta']
        self.width = self.height = user_model_settings['network']['L']
        self.state['sigma'] = np.full(self.width * self.height, -1, np.int8)
        self.state['magnetisation'] = sum(self.state['sigma']) * 1.

    async def step(self, vars_config, t):
        sigma = self.state['sigma']
        width = self.width
        height = self.height
        n = width * height
        betaj = self.beta * self.j

        for i in range(n):
            k = random.randint(0, n-1)
            s = 0
            if k % self.width != 0:
                s += sigma[k - 1]
            if (k + 1) % self.width != 0:
                s += sigma[k + 1]
            if (k - self.width) >= 0:
                s += sigma[k - width]
            if (k + self.width) < n:
                s += sigma[k + width]

            sigma[k] = 1 if random.random() > 1 / \
                (1 + np.exp(betaj * s)) else -1
        self.state['magnetisation'] = sum(self.state['sigma']) * 1.


def main():
    model_main(Model, ModelBackendSettings)


if __name__ == '__main__':
    main()
