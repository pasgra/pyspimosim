import sys
import os
import argparse
import logging
import asyncio
from pyspimosim.model_loader import get_models
from dataclasses import dataclass, field, fields, MISSING
from pyspimosim.servers import start_servers, start_web_server


root_dir = os.path.dirname(__file__)
default_root_dir = os.path.join(root_dir, "spimosim")
default_model_backend_dir = os.path.join(root_dir, "models")


def namespace_to_dataclass(DataClass, args, ignore=()):
    return DataClass(**{k: v for k, v in vars(args).items() if v is not None and k not in ignore})


def create_parser_from_data_class(class_, parser=None, taken_short_options=()):
    if parser is None:
        parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    short_options = set(taken_short_options)

    for field in sorted(fields(class_), key=lambda f: f.name):
        help_str = field.metadata.get("help", None)
        if field.default == MISSING and field.type != bool:
            if type(field.type) is list:
                parser.add_argument(
                    field.name, type=field.type[0], nargs="+", help=help_str)
            else:
                parser.add_argument(field.name, type=field.type, help=help_str)
            continue

        options = ["--" + field.name]
        possible_short_options = set(
            ["-" + field.name[0].upper(), "-" + field.name[0]]
        )
        short = sorted(list(possible_short_options.difference(short_options)))
        if len(short):
            options.append(short[-1])
            short_options.add(short[-1])
        if field.type == bool:
            action = "store_false" if field.default else "store_true"
            parser.add_argument(*options, action=action, help=help_str)
        elif type(field.type) is list:
            parser.add_argument(
                *options, type=field.type[0], nargs="+", default=field.default, help=help_str)
        else:
            parser.add_argument(*options, type=field.type,
                                nargs="?", default=field.default, help=help_str)

    return parser, short_options


class _HelpAction(argparse._HelpAction):

    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help()

        subparsers_actions = [
            action for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)]
        for subparsers_action in subparsers_actions:
            for choice, subparser in subparsers_action.choices.items():
                print("\n\nHelp for model '{}'".format(choice))
                print(subparser.format_help())

        parser.exit()


def parse_model_backend_dir_arg(args=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--model_backend_dir", "-M", default=default_model_backend_dir,
                        help="Search directory for models")
    return parser.parse_known_args(sys.argv)[0].model_backend_dir


def get_parser(models):
    parser = argparse.ArgumentParser(
        add_help=False, formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    subparsers = parser.add_subparsers(
        title="Available models to run", dest="model")
    subparsers.add_parser(
        "www_model", formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    _, taken_short_options = create_parser_from_data_class(
        BackendSettings, parser=parser)
    parser.add_argument('--help', "-h", "-?", action=_HelpAction, help='Help')

    for model_name, (Model, ModelBackendSettings) in models.items():
        create_parser_from_data_class(ModelBackendSettings, parser=subparsers.add_parser(
            model_name, formatter_class=argparse.ArgumentDefaultsHelpFormatter), taken_short_options=taken_short_options)

    try:
        import argcomplete
        argcomplete.autocomplete(parser)
    except:
        pass  # not fatal: bash completion is not available if argcomplete is not installed or fails

    return parser


def to_dataclasses(parsed_args, Model, ModelBackendSettings):
    not_backend_settings_fields = [
        f.name for f in fields(ModelBackendSettings)] + ["model"]
    not_model_backend_settings_fields = [
        f.name for f in fields(BackendSettings)] + ["model"]

    backend_settings = namespace_to_dataclass(
        BackendSettings, parsed_args, ignore=not_backend_settings_fields)
    model_backend_settings = namespace_to_dataclass(
        ModelBackendSettings, parsed_args, ignore=not_model_backend_settings_fields)
    if backend_settings.www_model_root == "":
        backend_settings.www_model_root = Model.get_www_model_root(root_dir)

    return backend_settings, model_backend_settings


def setup_logging():
    LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
    logging.basicConfig(level=LOGLEVEL)


@dataclass
class BackendSettings:
    model_backend_dir: str = field(default=default_model_backend_dir, metadata={
                                   "help": "Search directory for models"})
    www_root: str = field(default=default_root_dir, metadata={
                          "help": "Root directory for the web server"})
    www_address: str = field(default="0.0.0.0", metadata={
                             "help": "IP address for the web server"})
    www_port: int = field(default=8000, metadata={
                          "help": "Port for the web server"})
    www_model_root: str = field(default="", metadata={
                                "help": "Directory containing index.html, model_config.js, model_info.html for model"})
    websocket_address: str = field(default="0.0.0.0", metadata={
                                   "help": "IP address for the websocket server"})
    websocket_port: int = field(default=8090, metadata={
                                "help": "Port for the websocket server"})


async def www_model_main(Model, backend_settings, model_backend_settings, custom_tornado_handlers=()):
    start_web_server(Model, backend_settings,
                     model_backend_settings, custom_tornado_handlers=())

    # Start IO/Event loop
    shutdown_event = asyncio.Event()
    await shutdown_event.wait()


def main(custom_tornado_handlers=()):
    setup_logging()
    models = get_models(parse_model_backend_dir_arg())
    parser = get_parser(models)
    parsed_args = parser.parse_args()
    if not parsed_args.model:
        parsed_args.model = "www_model"

    Model, ModelBackendSettings = models[parsed_args.model]
    backend_settings, model_backend_settings = to_dataclasses(
        parsed_args, Model, ModelBackendSettings)
    if parsed_args.model == "www_model":
        asyncio.get_event_loop().run_until_complete(www_model_main(Model, backend_settings,
                                                                   model_backend_settings, custom_tornado_handlers=custom_tornado_handlers))
    else:
        asyncio.get_event_loop().run_until_complete(start_servers(Model, backend_settings,
                                                                  model_backend_settings, custom_tornado_handlers=custom_tornado_handlers))


def model_main(Model, ModelBackendSettings, custom_tornado_handlers=()):
    setup_logging()
    parser, taken_short_options = create_parser_from_data_class(
        BackendSettings)
    create_parser_from_data_class(
        ModelBackendSettings, parser=parser, taken_short_options=taken_short_options)
    parsed_args = parser.parse_args()
    backend_settings, model_backend_settings = to_dataclasses(
        parsed_args, Model, ModelBackendSettings)
    asyncio.get_event_loop().run_until_complete(start_servers(Model, backend_settings,
                                                              model_backend_settings, custom_tornado_handlers=custom_tornado_handlers))
