# pymongo-document-modeling

Create data model backed with pymongo called: Document which have ability of polymorphism, and inheritance.

## Feature

This document modeling library designed with OOP as a goal. Therefore it can associate field, and inherit it to its subclasses. 

## How to Use

```
class SimpleDocument(doc.Doc):
    int_val = doc.FieldNumeric()
    str_val = doc.FieldString(default="default_value_of_string")

    class Meta:
        collection_name = "simple_document"
```

This allow 

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
