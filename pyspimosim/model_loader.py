import importlib
import os
import sys


def load_classes(class_name, dirname):
    sys.path = [dirname] + sys.path
    module = importlib.import_module(class_name)
    sys.path = sys.path[1:]
    Model = getattr(module, 'Model')
    ModelBackendSettings = getattr(module, 'ModelBackendSettings')
    return Model, ModelBackendSettings


def get_model_names(dirname):
    for path in os.listdir(dirname):
        if not os.path.isdir(os.path.join(dirname, path)) and path.endswith("_model.py"):
            yield path[:-len(".py")]


def get_models(dirname):
    models = {}

    for model in get_model_names(dirname):
        Model, ModelBackendSettings = load_classes(model, dirname)
        models[model] = (Model, ModelBackendSettings)

    return models
