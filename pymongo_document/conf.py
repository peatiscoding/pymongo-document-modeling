import os
import configparser
import pymongo
from errors import DeveloperFault


# default config - will be override by settings module
class Configuration(object):

    CONF = {
        'default': {
            'connection_string': 'mongodb://localhost:27017/',
            'database_name': 'default_database'
        }
    }


def update_config(config_path):

    if os.path.isfile(config_path):
        path = config_path
    elif os.path.isdir(config_path):
        path = os.path.join(config_path, 'pymongo-connectors.ini')
    else:
        raise DeveloperFault('Unknown config_path=%s' % config_path)

    if os.path.isfile(path):
        config = configparser.ConfigParser()
        config.read(path)

        # Validate config file
        def validate_configuration(pair):
            name, conf = pair
            if 'connection_string' not in conf:
                raise DeveloperFault('Bad configuration: "connection_string" is missing from "%s" connection.' % name)

        if 'default' not in config:
            raise DeveloperFault('Bad configuration: "default" connection is required.')

        map(validate_configuration, filter(lambda o: o[0] != 'DEFAULT', config.iteritems()))

        Configuration.CONF = config


# internal connector method.
def get_connection(connection_name='default'):
    if connection_name not in Configuration.CONF:
        raise DeveloperFault('Unknown connection_name: "%s"' % connection_name)

    cnf = Configuration.CONF[connection_name]
    database_name = cnf['database_name'] if 'database_name' in cnf else 'default_database'
    return pymongo.MongoClient(cnf['connection_string']).__getattr__(database_name)
