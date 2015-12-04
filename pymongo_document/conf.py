import pymongo
import os
import configparser
from errors import DeveloperFault

print("CWD %s" % os.getcwd())
path = os.path.join(os.getcwd(), 'pymongo-connectors.ini')

if os.path.isfile(path):
    config = configparser.ConfigParser()
    config.read(path)
else:
    config = {
        'default': {
            'connection_string': 'mongodb://localhost:27017/',
            'database_name': 'default_database'
        }
    }


# Validate config file
def validate_configuration(pair):
    name, conf = pair
    print dict(conf)
    if 'connection_string' not in conf:
        raise DeveloperFault('Bad configuration: "connection_string" is missing from "%s" connection.' % name)

if 'default' not in config:
    raise DeveloperFault('Bad configuration: "default" connection is required.')

map(validate_configuration, filter(lambda o: o[0] != 'DEFAULT', config.iteritems()))


# internal connector method.
def get_connection(connection_name='default'):
    if connection_name not in config:
        raise DeveloperFault('Unknown connection_name: "%s"' % connection_name)

    conf = config[connection_name]
    database_name = conf['database_name'] if 'database_name' in conf else 'default_database'
    return pymongo.MongoClient(conf['connection_string']).__getattr__(database_name)
