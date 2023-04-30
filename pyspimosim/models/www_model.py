#!/usr/bin/env python3

# This script supports autocompletion with argcomplete: PYTHON_ARGCOMPLETE_OK

import os

from pyspimosim.base_model import BaseModel, ModelBackendSettings as BaseModelBackendSettings
from pyspimosim.main import model_main
from dataclasses import dataclass


@dataclass
class WWWModelBackendSettings(BaseModelBackendSettings):
    pass


class WWWModel(BaseModel):
    name = "www_model"

    @classmethod
    def get_www_model_root(cls, root_dir):
        return os.path.join(root_dir, "spimosim")


Model = WWWModel
ModelBackendSettings = WWWModelBackendSettings


def main():
    model_main(Model, ModelBackendSettings)


if __name__ == '__main__':
    main()
