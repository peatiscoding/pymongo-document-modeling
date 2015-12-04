pymongo-document-modeling
=========================

Create data model backed with pymongo called: Document which have
ability of polymorphism, and inheritance.

Feature
-------

This document modeling library designed with OOP as a goal. Therefore it
can associate field, and inherit it to its subclasses.

Installation
------------

Begin with installation

.. code:: python

    > pip install pymongo-document-modeling
    
Configuration
-------------

Once you have installed ``pymongo-document-modeling`` module. Now you 
can start configure your pymongo. Simply create a configuration file called
``pymongo-connectors.ini`` and add 'default' section in. Then state ``connection_string`` 
and ``database_name`` keys with your values.

Here is a dirty example.

.. code:: python

    [default]
    connection_string = mongodb://localhost:27017/
    database_name = test_beds
    [test_data_pool]
    connection_string = mongodb://localhost:27017/
    database_name = test_data_pool

For more advance cases. You can actually specify many connection sections as you want 
(But ``default`` section is required).
 
Now within your model, you can reference this connector name. If omitted ``default`` will be used. 
(See next example ``Meta`` class).

How to Use
----------

Learn by example is simplest, and fastest. Here are some quick and dirty
simple class examples.

.. code:: python
    
    from pymongo_document import documents as doc

    class SimpleDocument(doc.Doc):
        int_val = doc.FieldNumeric()
        str_val = doc.FieldString(default="default_value_of_string")

        class Meta:
            collection_name = "simple_document"         # Special class to annotate the document name to be saved.
            connection_name = "test_data_pool"          # Will reference your "test_data_pool" connection

Load and Save is as simple as Django’s Model.

.. code:: python

    d = SimpleDocument()
    d.int_val = 500
    d.save() # document is saved to your mongodb

    loaded = SimpleDocument(d.object_id)
    print d.int_val # 500
    print d.str_Val # default_value_of_string

For more complex classes, you can inherit from existing class, override
existing fields.

.. code:: python

    class ABitComplexDocument(SimpleDocument):
        int_val_2 = doc.FieldNumeric(none=False)
        str_val = doc.FieldString(default="default_value_changed")

        class Meta:
            collection_name = ":complex_1"  # use ':' to annotate the system to let this data model shared parent's collection

Mongo doesn’t have join, but we could establish connection between
collection. We facilitate this by nesting them in a list of documents.

.. code:: python

    class HolderOfSimpleDocuments(doc.Doc):
        list_of_docs = doc.FieldList(doc.FieldDoc(SimpleDocument))

        class Meta:
            collection_name = "document_holders"

There are many more type of example, please see the complete list of
documentation below.

Running this project
====================

Getting Ready
-------------

In your working directory, create python environment, let’s say ``env``
is your environment name.

``virtualenv env``

In your python environment, install dependencies:

1. ``env/bin/pip install pymongo``
2. ``env/bin/pip install six``

Fire up your test bed,
----------------------

In your console: start your ``mongod``.

``> sudo mongod``

Run the test

``> env/bin/python -m unittest discover``

Currently working on complete document of fields.

References
==========

Document
--------

Document is designed with ``django`` model in mind. With help of special
``Meta`` class, we can beautifully annotate the document with
``indices``, and much more.

To create a new document, you can simply start by extending ``Doc``
class.

.. code:: python

    from pymongo_document import documents as doc

    class MySimpleDoc(doc.Doc):
        # Define fields here
        name = doc.FieldString(max_length=30, none=False)

        class Meta:
            collection_name = 'my_simple_doc'

With this code, ``MySimpleDoc`` will be created when this module is
imported. This ``MySimpleDoc`` will have exactly 2 fields.

1. Field ``name`` is created as a string field, cannot be ``None``, and
   text length must not exceeds 30.
2. Field ``object_id`` is also (automatically) created by inherit it
   from ``doc.Doc`` class. You can explicitly override this field, by
   redeclare the field with exact same name. The type can be totally
   different.

.. code:: python

    o = MySimpleDoc()           # Create a new MySimpleDoc instance
    o.save()                    # Error thrown, 'name' is required.
    o.name = 1                  # Error thrown, in correct type, 'basestring' is required.
    o.name = 'peatiscoding'     # Set name
    o.save()                    # Successfully saved to collection 'my_simple_doc'

… TBC

Fields
------

FieldObjectId
~~~~~~~~~~~~~

Use this field to store any ``ObjectId``. But If you would like to store
another document reference. Try ``FieldDoc`` or ``FieldAnyDoc`` instead.

*Usage*

.. code:: python

    class SimpleDocument(doc.Doc):
        oid = FieldObjectId()

ObjectId field accepts ``bson.ObjectId`` instance, or ``bson.ObjectId``
compatible string (24 alphanumeric string).

*Note* that normally if you inherit from ``Doc`` you will automatically
get ``object_id`` field for free.

FieldNumeric
~~~~~~~~~~~~

Use this field to store any numeric numbers.

*Usage*

.. code:: python

    class SimpleDocument(doc.Doc):
        amount = FieldNumeric()