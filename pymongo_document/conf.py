import pymongo


# internal connector method.
def db():
    # FIXME: Need to utilise configuration from settings.py
    return pymongo.MongoClient().my_database
