#!/usr/bin/env python3

# This script supports autocompletion with argcomplete: PYTHON_ARGCOMPLETE_OK

import os
from dataclasses import dataclass, field
from pyspimosim.main import model_main, root_dir
from pyspimosim.base_model import ModelBackendSettings as BaseModelBackendSettings
from pyspimosim.csv_pipe_model import CSVPipeModel, CSVPipeWriter, InstanceId


class Model(CSVPipeModel):
    name = "two_col_csv"

    data_file_fields = [
        ("x", 1), ("y", 1)
    ]

    settings_fields = []

    def init_pipe_writer(self, model_backend_settings):
        self.csv_pipe_writer = Writer("settings-out.csv", self.settings_fields)


class Writer(CSVPipeWriter):
    def go_on(self, t):
        pass


@dataclass
class ModelBackendSettings(BaseModelBackendSettings):
    workbasedir: str = field(default=os.path.join(root_dir, "tests", "two_col_csv_data"), metadata={
                             "help": "The working directory will be <workbasedir>/<instance_id>"})
    instance_id: InstanceId = field(default=InstanceId("red_white"), metadata={
                                    "help": "The working directory will be <workbasedir>/<instance_id>"})
    setting_file: str = field(default="settings.csv", metadata={
                              "help": "File name (inside working directory) for the *.csv file or pipe for settings (and more)"})
    data_file: str = field(default="data.csv", metadata={
                           "help": "File name (inside working directory) for the *.csv file or pipe for generated data"})
    data_file_skiplines: int = field(default=0, metadata={
                                     "help": "Size of the ignored header of the file specified by --output"})
    no_new_run: bool = field(default=True, metadata={
                             "help": "Generate new data"})
    data_is_final: bool = field(default=True, metadata={
                                "help": "Continue reading after reaching end of file and wait for new data"})


def main():
    model_main(Model, ModelBackendSettings)


if __name__ == '__main__':
    main()
