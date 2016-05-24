from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pymongo-document-modeling',
    version='0.9.1.dev5',
    description='PyMongo data modeling library',
    long_description=long_description,
    url='https://github.com/peatiscoding/pymongo-document-modeling',
    author='peatiscoding',
    author_email='freeuxer@gmail.com',
    license='Apache License, Version 2.0',
    # see: https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Topic :: Database',
        'Topic :: Software Development :: Libraries',
    ],
    keywords=['pymongo', 'database', 'mongodb', 'modeling'],
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    install_requires=['six', 'pymongo', 'configparser'],
)
