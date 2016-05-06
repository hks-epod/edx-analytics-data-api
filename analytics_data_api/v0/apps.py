from importlib import import_module

from elasticsearch_dsl import connections

from django.apps import AppConfig
from django.conf import settings


class ApiAppConfig(AppConfig):

    name = 'analytics_data_api.v0'

    def ready(self):
        super(ApiAppConfig, self).ready()
        if settings.ELASTICSEARCH_LEARNERS_HOST:
            connection_params = {'hosts': [settings.ELASTICSEARCH_LEARNERS_HOST]}
            if settings.ELASTICSEARCH_CONNECTION_CLASS:
                connection_params['connection_class'] = \
                    load_fully_qualified_definition(settings.ELASTICSEARCH_CONNECTION_CLASS)

            # aws settings
            connection_params['aws_access_key_id'] = settings.ELASTICSEARCH_AWS_ACCESS_KEY_ID
            connection_params['aws_secret_access_key'] = settings.ELASTICSEARCH_AWS_SECRET_ACCESS_KEY
            connection_params['region'] = settings.ELASTICSEARCH_CONNECTION_DEFAULT_REGION

            # Remove 'None' values so that we don't overwrite defaults
            connection_params = {key: val for key, val in connection_params.items() if val is not None}

            connections.connections.create_connection(**connection_params)


def load_fully_qualified_definition(definition):
    """ Returns the class given the full definition. """
    module_name, class_name = definition.rsplit('.', 1)
    module = import_module(module_name)
    return getattr(module, class_name)
