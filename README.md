# pymongo-document-modeling

Create data model backed with pymongo called: Document which have ability of polymorphism, and inheritance.

## Feature

This document modeling library designed with OOP as a goal. Therefore it can associate field, and inherit it to its subclasses. 

## How to Use

Simple class a like schema definition.

```python
class SimpleDocument(doc.Doc):
    int_val = doc.FieldNumeric()
    str_val = doc.FieldString(default="default_value_of_string")

    class Meta:
        collection_name = "simple_document"
```

Inherit from existing class.

```python
class ABitComplexDocument(SimpleDocument):
    int_val_2 = doc.FieldNumeric(none=False)
    str_val = doc.FieldString(default="default_value_changed")

    class Meta:
        collection_name = ":complex_1"  # use ':' to annotate the system that this will share the same collection
```

Nest them in a list of documents.

```python
class HolderOfSimpleDocuments(doc.Doc):
    list_of_docs = doc.FieldList(doc.FieldDoc(SimpleDocument))

    class Meta:
        collection_name = "document_holders"
```

# Running this project

## Getting Ready

In your working directory, create python environment, let's say ```env``` is your environment name.

```virtualenv env```

In your python environment, install dependencies: 

1. ```env/bin/pip install pymongo```
1. ```env/bin/pip install six```

## Fire up your test bed,

In your console: Starts your mongod engine.

``` > sudo mongod```

Run the test

``` > env/bin/python -m unittest discover```
