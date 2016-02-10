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
can start configure your pymongo. To state the configuration file, first prepare your config.

Here is a dirty example of configuration file.

.. code:: python

    [default]
    connection_string = mongodb://localhost:27017/
    database_name = test_beds
    [test_data_pool]
    connection_string = mongodb://localhost:27017/
    database_name = test_data_pool

For more advance cases. You can actually specify many connection sections as you want 
(But ``default`` section is required).

Now let the system know where your configuration file is. To do this, call ``conf.update_config()`` 
before your declare your first class.

.. code:: python

    from pymongo_document import conf
    
    # example a - specify the file
    conf.update_config('conf/my-config.ini')        # read config from os.path.getcwd() + 'conf/my-config.ini'
    # example b - specify directory (default config file name will be assumed).
    conf.update_config('conf/')                     # read config from os.path.getcwd() + 'conf/pymongo-connectors.ini'
 
Lastly, within your model, you can reference this connector name. If omitted ``default`` will be used. 
(See first example in Quick start section's ``Meta`` class).

*Note* If ``conf.update_config()`` never get invoked, this default configuration will be assumed.

.. code:: python
    
    [default]
    connection_string = mongodb://localhost:27017/
    database_name = default_database

Quick Start
-----------

Learn by example is simplest, and fastest. Here are some quick and dirty
simple class examples.

.. code:: python
    
    from pymongo_document import documents as doc       # Import library module as "doc"

    class SimpleDocument(doc.Doc):
        int_val = doc.FieldNumeric()
        str_val = doc.FieldString(default="default_value_of_string")

        class Meta:
            collection_name = "simple_document"         # Special class to annotate the document name to be saved.
            connection_name = "test_data_pool"          # Explicitly state connection_name, (If omitted, 'default' will be used)

Load and Save is as simple as Django’s Model.

.. code:: python

    d = SimpleDocument()
    d.int_val = 500
    d.save() # document is saved to your mongodb

    loaded = SimpleDocument(d.object_id)
    print d.int_val         # 500
    print d.str_Val         # default_value_of_string
    print d.object_id       # auto generated bson.ObjectId

For more complex classes, you can inherit from existing class, override
existing fields.

.. code:: python

    class ABitComplexDocument(SimpleDocument):          # Extend existing model
        int_val_2 = doc.FieldNumeric(none=False)        # Add new field
        str_val = doc.FieldString(default="default_value_changed")      # Override existing model's field

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

References
==========

Document Object
---------------

Document is designed with ``django`` model in mind. With help of special
``Meta`` class, we can beautifully annotate the document with
``indices``, ``connection_name``, ``collection_name`` and more.

To create a new document, you can simply start by extending ``Doc`` class.

.. code:: python

    from pymongo_document import documents as doc

    class MySimpleDoc(doc.Doc):
        # Define fields here
        name = doc.FieldString(max_length=30, none=False)

        class Meta:
            collection_name = 'my_simple_doc'

With this code, ``MySimpleDoc`` will be created when this module is
imported. This ``MySimpleDoc`` will have exactly 2 fields (not 1).

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

Document.manager
----------------

All documents class will be equipped with ``manager`` object (``pymongo_document.Docs`` class).
``manager`` is just like ``objects`` in Django's Model's manager. Allows user to ``find`` , ``update``,
or ``delete`` documents.

Find API
~~~~~~~~

To make things easy, I've decided to use pymongo existing ``find`` api. For complete doc
see `find() document`_. pymongo collection's ``find()`` method normally return ``dict`` as output.
Instead of returning simple ``dict``, the ``Document`` instance will be returned.

.. _find() document: http://api.mongodb.org/python/current/api/pymongo/collection.html#pymongo.collection.Collection.find

.. code:: python

    o = MySimpleDoc()
    o.save()

    cursor = MySimpleDoc.manager.find().sort('_id') # use Cursor's method as pymongo did.
    for a in cursor:
        print "%s" % a.object_id                    # cursor returned objects is now already inflated as Document.

FieldSpecAware Object
---------------------

``Doc`` class is inherited from ``FieldSpecAware`` class. ``FieldSpecAware`` taken care 
of ``Field`` detection, and overseer them in translating from python object, to document 
(saving format for mongodb). 

Normally you will use ``FieldSpecAware`` with ``FieldNested``. So that you can define a 
dict within another document. See @FieldNested for more information.

Fields
------

Every field are customisable via the use of ``**kwargs`` of which each options will be provided in the
sample per each individual fields below.

In addition, every field is compatible with assigning its own ``validator`` as well. To add your own
validators. Create a field, then specific validators keyword argument in field creation.

Validator can be defined in 2 styles.

* ``Callable`` - if you supplied validators as a simple callable, then you are responsible to raise a proper ``FieldValidationError`` manually.
* ``(Callable, basestring)`` - if ``callable`` returns True, ``basestring`` will be raised as an Error message.

Here is an example.

.. code:: python

     def in_the_past_or_throw(value, name):
            if isinstance(value, datetime) and value < datetime.now():
                return
            raise err.FieldValidationError(value, 'Value must be past', name)

    class TestMeDocument(doc.Doc):
        positive_number = doc.FieldNumeric(validators=[(lambda v: v < 0, 'positive number is required')])
        even_number = doc.FieldNumeric(validators=[(lambda v: v % 2 == 1, 'even number only')])
        negative_odd_number = doc.FieldNumeric(validators=[
            (lambda v: v > 0, 'negative number is required'),
            (lambda v: v % 2 == 0, 'odd number is required')
        ])
        custom_value = doc.FieldDateTime(validators=[in_the_past_or_throw])  # Callable style

By assigning incorrect value ``FieldValidationError`` will be raised.

FieldObjectId
~~~~~~~~~~~~~

Use this field to store any ``ObjectId``. But If you would like to store
another document reference. Try ``FieldDoc`` or ``FieldAnyDoc`` instead.

*Usage*

.. code:: python

    class SimpleDocument(doc.Doc):
        oid = doc.FieldObjectId()

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
        VALUE_A = 1
        VALUE_B = 2
        VALUE_C = 3
        VALUES = (
            (VALUE_A, '1st value'),
            (VALUE_B, '2nd value'),
            (VALUE_C, '3rd value')
        )
        
        amount1 = doc.FieldNumeric(default=3, max_value=50, min_value=10)
        amount2 = doc.FieldNumeric(max_value=40, none=False)
        amount3 = doc.FieldNumeric()        # no max, no min, can be None, no default
        amount4 = doc.FieldNumeric(choices=VALUES)

* ``max_value`` - (numeric) set upper bound of field. Default is None (no upper bound).
* ``min_value`` - (numeric) set lower bound of field. Default is None (no lower bound).
* ``default`` - (numeric) set a default value for this field. Default is None.
* ``none`` - (boolean) set to False to prohibit None value for this field. Default is True.
* ``choices`` - (tuple, list) set possible values for the field. Default is None.

FieldString
~~~~~~~~~~~

Use this file to store any ``basestring`` instance.

*Usage*

.. code:: python

    class SimpleDocument(doc.Doc):
        VALUE_A = 'A'
        VALUE_B = 'B'
        VALUE_C = 'C'
        VAULES = (
            (VALUE_A, 'A description'),
            (VALUE_B, 'B description'),
            (VALUE_C, 'C description'),
        )
        str_value = doc.FieldNumeric(default="default_string", max_length=10)
        fixed_length_str_value = doc.FieldString(fixed_length=2)
        fixed_choices_str_value = doc.FieldString(choices=VALUES, default=VALUE_A)
        fixed_pattern_str_value = doc.FieldString(pattern=r'[a-z]{2}\d{5}3-[A-Z]{2}')

* ``pattern`` - (SRE_Pattern|regex pattern string) set a required pattern for input string. Default is None.
* ``max_length`` - (numeric) set maximum character count. Default is None (no upper bound).
* ``fix_length`` - (numeric) set constant character count. Default is None (no upper bound).
* ``default`` - (numeric) set a default value for this field. Default is None.
* ``none`` - (boolean) set to False to prohibit None value for this field. Default is True.
* ``choices`` - (tuple, list) set possible values for the field. Default is None.
        

FieldDict
~~~~~~~~~

Use this field to store complete any python dict without schema.

*Usage*

.. code:: python

    class SimpleDocument(doc.Doc):
        data = doc.FieldDict()

* ``default`` - (dict) set a default value for this field. Default is None.
* ``none`` - (boolean) set to False to prohibit None value for this field. Default is True.


FieldTuple

Use this field to store a FieldSpec value that obligated by each rule based on position on the list.

*Usage*

.. code:: python

    class TupleFieldDocument(doc.Doc):
        data = doc.FieldTuple(doc.FieldNumeric(), doc.FieldString(), doc.FieldNumeric())

* ``default`` - (tuple) set a default value for this field. Default is None.
* ``none`` - (boolean) set to False to prohibit Nont value for this field. Default is True.

Unlike ``FieldList``, ``FieldTuple`` constructor accept ``*args`` as argument of ``FieldSpec``. Each ``FieldSpec``
correspond to Field specification for each element on the tuple respectively.

Therefore ``FieldTuple`` assignment required an exact tuple size to the ``FieldSpec`` provided in constructor.

.. code:: python

    o = TupleFieldDocument()
    o.data = (12, 'test', 12)       # this is okay
    o.data = (12, 'test')           # raise doc.FieldValidationError invalid tuple size
    o.data = ('test', 24, 45)       # raise doc.FieldValidationError index 1 should be integer, index 2 should be text
