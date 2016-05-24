from bson import ObjectId
from conf import get_connection
from errors import DeveloperFault, DocumentValidationError, FieldValidationError
from pymongo.cursor import Cursor
import helpers as helper
import gettext as _
import datetime, time
import inspect
import six
import re
import copy

__author__ = "peatiscoding"


class MaskedCursor(Cursor):
    """
    Cursor
    """
    def __init__(self, *args, **kwargs):
        super(MaskedCursor, self).__init__(*args, **kwargs)
        self.inflate_callback = None

    def next(self):
        o = super(MaskedCursor, self).next()
        return self.inflate_callback(o) if self.inflate_callback else o

    def __len__(self):
        return self.count()

    def __getitem__(self, item):
        o = super(MaskedCursor, self).__getitem__(item)
        return self.inflate_callback(o) if isinstance(o, dict) and self.inflate_callback else o


class Docs(object):
    """
    Database Manager
    """
    installed = {}
    _on_delete = {}

    def __init__(self, collection_name, connection_name='default'):
        super(Docs, self).__init__()
        db_name, sub_name = collection_name.split(":", 1) if ":" in collection_name else (collection_name, None)
        self.collection_name = collection_name
        self.sub_collection_name = sub_name
        self.db_name = db_name
        # properly configure db object.
        self.db = get_connection(connection_name)

        if db_name is None:
            raise DeveloperFault("Unable to create empty database name document manager")
        self.o = self.db[db_name]

    def write(self, document, **kwargs):
        document['_id'] = kwargs.get('object_id', document['_id'] or None)
        if document['_id'] is None:
            document.pop("_id")
        if self.sub_collection_name is not None:
            document['_subtype'] = self.sub_collection_name
        return self.o.save(document)

    def delete(self, cond=None, verbose=False):
        """
        Call pymongo's delete_many, cascade delete logic based on primary_key attracted from deleted instances.

        :param cond:
        :param verbose:
        :return:
        """
        cond = {} if cond is None else cond
        on_delete = self._on_delete[self.db_name] if self.db_name in self._on_delete else []
        if verbose:
            print 'Deleting "%s": %s' % (self.db_name, cond)

        # If there are listeners
        if len(on_delete) > 0:
            # Calculate ids - and delete them.
            ids = self.o.find(cond).distinct('_id')
            map(lambda de: de(ids, verbose), on_delete)
        self.o.delete_many(cond)

    def update(self, cond, update, **kwargs):
        """
        Call pymongo update_many directly, (upsert=False) - no field validation will be applied.

        Use this method at your own risk.

        :param cond:
        :param update:
        :param kwargs:
        :return:
        """
        if cond is None:
            cond = {}
        if update is None:
            raise DeveloperFault('update cannot be none')
        verbose = kwargs.pop('verbose', False)
        if verbose:
            print 'Updating "%s": %s' % (self.db_name, cond)
        self.o.update_many(cond, update, upsert=False)

    def find(self, *args, **kwargs):
        cache = {}

        def inflate(doc):
            key = str(doc['_id'])
            if key not in cache:
                doc_key = self.collection_name
                if '_subtype' in doc:
                    subtype = doc.pop('_subtype')
                    doc_key = "%s:%s" % (self.db_name, subtype)
                if doc_key not in Docs.installed:
                    raise DeveloperFault("Unknown document type:%s" % doc_key)
                o = Docs.installed[doc_key]()
                o.inflate(doc)
                cache[key] = o
            return cache[key]

        r = MaskedCursor(self.o, *args, **kwargs)
        r.inflate_callback = inflate
        return r

    def count(self, cond, **kwargs):
        if cond is None:
            cond = {}
        cond.update(kwargs)
        return self.o.find(cond, []).count()

    def _create_index(self, key, options):
        index_name = self.o.create_index(key, **options)
        print("\t=> Created index %s %s = %s" % (key, options, index_name))
        return index_name

    def _add_delete_trigger(self, trigger_source_db_name, reference_field):
        if trigger_source_db_name not in self._on_delete:
            self._on_delete[trigger_source_db_name] = []
        self._on_delete[trigger_source_db_name].append(lambda ids, v: self.delete({reference_field: {'$in': ids}}, v))
        print("\t=> Created delete trigger: '%s' will chain delete collection='%s', field='%s'" % (trigger_source_db_name, self.db_name, reference_field))

    @classmethod
    def register(cls, doc_class, indices=[], references=[]):
        """

        :param doc_class: registry document class
        :param indices: list of required index to be added to mongo
        :param references: list of foreign key tuple of ... (collection_name, class_field_name).
        :return:
        """

        # if sub_name exists Let's validate if the class is an extension of its parent
        if doc_class.manager.sub_collection_name is not None and not issubclass(doc_class, Docs.installed[doc_class.manager.db_name]):
            raise DeveloperFault("Extension of collection must be extension of same class hierarchy.")

        Docs.installed[doc_class.manager.collection_name] = doc_class
        # Call create_index
        map(lambda (k, o): doc_class.manager._create_index(k, o), indices)
        map(lambda (c, f): doc_class.manager._add_delete_trigger(c, f), references)

    @classmethod
    def factory(cls, collection_name, object_id=None):
        if object_id is None:
            return Docs.installed[collection_name]()
        man = cls.installed[collection_name].manager
        raw = man.o.find_one(helper.object_id(object_id))
        doc_key = man.db_name
        if '_subtype' in raw:
            subtype = raw.pop('_subtype')
            doc_key = "%s:%s" % (man.db_name, subtype)
        if doc_key not in Docs.installed:
            raise DeveloperFault("Unknown document type:%s" % doc_key)
        o = cls.installed[doc_key]()
        o.inflate(raw)
        return o

    @classmethod
    def factory_doc(cls, collection_name):
        if collection_name in cls.installed:
            return cls.installed[collection_name]
        raise DeveloperFault('Unknown collection_name %s' % collection_name)


# FieldSpec
class FieldSpec(object):

    def __init__(self, classes, **kwargs):
        super(FieldSpec, self).__init__()
        if isinstance(classes, tuple):
            self.classes = classes
        else:
            self.classes = (classes,)
        self.transient = kwargs.get('transient', False)   # if set, it is Subclass responsibility to handle data injection through populate method.
        self.validators = kwargs.get('validators', [])
        self.default = kwargs.get('default', None)
        self.choices = kwargs.get('choices', {})
        self.max_length = kwargs.get('max_length', 0)
        self.fixed_length = kwargs.get('fixed_length', None)
        self.none = kwargs.get('none', True)
        self.key = kwargs.get('key', None)
        self.omit_if_none = kwargs.get('omit_if_none', False)       # If value is none, act as transient

        # Make sure self.choices is dictionary
        self.choices = dict(self.choices)

        self.builtin_validators = []

        # Create built-in validators
        if not self.none:
            self.add_named_validator(lambda v: v is None, "Cannot assign None to Non-none field.")
        if len(self.classes) > 0:
            self.add_named_validator(lambda v: not isinstance(v, self.classes), "Invalid data type.")
        if self.choices is not None and len(self.choices) > 0:
            self.add_named_validator(lambda v: v not in self.choices, "Value is not within choices.")
        if self.fixed_length is not None:
            self.add_named_validator(lambda v: len(v) != self.fixed_length, "Value must be %s long." % self.fixed_length)
            if self.max_length > 0:
                raise DeveloperFault("max_length, and fixed_length cannot be used together.")
        if self.max_length > 0:
            self.add_named_validator(lambda v: len(v) > self.max_length, "Value is not be longer than %s." % self.max_length)

        # Sanitize validators
        def validate_and_raise(lambda_callback, throw):
            def wrapped(v, n):
                if lambda_callback(v):
                    raise FieldValidationError(v, throw, n)
            return wrapped

        for i, v in enumerate(self.validators):
            if callable(v):
                pass
            elif isinstance(v, tuple) and callable(v[0]) and isinstance(v[1], basestring):
                self.validators[i] = validate_and_raise(v[0], v[1])
            else:
                raise DeveloperFault('Bad validators %s' % v)

    def add_named_validator(self, callback, message):
        def callme(value, name):
            if callback(value):
                raise FieldValidationError(value, message, name)
        self.builtin_validators.append(callme)

    def validate(self, value, name):
        if self.none and value is None:
            return
        map(lambda v: v(value, name), self.builtin_validators + self.validators)

    def to_serialized(self, value):
        return value

    def from_serialized(self, value):
        return value

    def to_document(self, value):
        return value

    def from_document(self, value):
        return value

    def from_python(self, value):
        return value

    def populate(self, value, next_path):
        """
        Normally you don't need to override this method.
        This method act as a manipulation of the values for nested Doc only.
        / As nested doc may easily caused a 'Circular reference problem'. So we need
        user to explicitly called for population of such field.
        :param next_path:
        :return: void
        """
        return value

    def is_required(self):
        return not self.none


class FieldObjectId(FieldSpec):

    def __init__(self, **kwargs):
        super(FieldObjectId, self).__init__(ObjectId, **kwargs)

    def from_serialized(self, value):
        return value and ObjectId(value)

    def to_serialized(self, value):
        return value and str(value)

    @staticmethod
    def new_id():
        return ObjectId()


class FieldDateTime(FieldSpec):

    def __init__(self, **kwargs):
        super(FieldDateTime, self).__init__(datetime.datetime, **kwargs)

    def from_serialized(self, value):
        return value and datetime.datetime.fromtimestamp(value)

    def to_serialized(self, value):
        return value and time.mktime(value.timetuple())


class FieldBoolean(FieldSpec):

    def __init__(self, **kwargs):
        super(FieldBoolean, self).__init__(bool, **kwargs)

    def from_python(self, value):
        return value and bool(value) or value

    def from_serialized(self, value):
        return value and bool(value) or value


class FieldNumeric(FieldSpec):

    def __init__(self, **kwargs):
        max_value = kwargs.pop('max_value', None)
        min_value = kwargs.pop('min_value', None)
        if max_value is not None or min_value is not None:
            if max_value is not None and min_value is not None and max_value <= min_value:
                raise DeveloperFault('max_value must be greater than min_value')

            def validate_min_max(value, name):
                if max_value is not None and value > max_value:
                    raise FieldValidationError(value, 'must be less than %s' % max_value, name)
                if min_value is not None and value < min_value:
                    raise FieldValidationError(value, 'must be greater than %s' % min_value, name)

            # update kwargs
            kwargs.update({
                'validators': kwargs.pop('validators', []) + [validate_min_max]
            })

        super(FieldNumeric, self).__init__((int, float, long), **kwargs)


class FieldString(FieldSpec):

    def __init__(self, **kwargs):
        pattern = kwargs.pop('pattern', None)
        if pattern is not None:
            if not hasattr(pattern, 'match') or not callable(getattr(pattern, 'match')):
                pattern = re.compile(pattern)

            def validate_regex(value, name):
                if pattern.match(value) is None:
                    raise FieldValidationError(value, 'must match given pattern', name)
            kwargs.update({
                'validators': kwargs.pop('validators', []) + [validate_regex]
            })
            del validate_regex
        super(FieldString, self).__init__(basestring, **kwargs)

    def from_python(self, value):
        return value and unicode(value) or value

    def from_serialized(self, value):
        return value and unicode(value) or value


class FieldAnyDoc(FieldSpec):

    def __init__(self, **kwargs):
        super(FieldAnyDoc, self).__init__((tuple, list, Doc), **kwargs)

    def to_document(self, value):
        if value and isinstance(value, (tuple, list)):
            return [value[0], value[1]]         # Make sure we have a list placed there.
        if value and isinstance(value, Doc):
            return [value.object_id, value.manager.collection_name]
        return None

    def from_document(self, value):
        # Must supplied as [id, type]
        return value

    def from_serialized(self, value):
        # Must supplied, [id, type]
        if not self.none and value is not None:
            assert isinstance(value, (tuple, list)) and len(value) == 2 and isinstance(value[1], basestring)
            if isinstance(value[0], basestring):
                value[0] = ObjectId(value[0])
        return value

    def to_serialized(self, value):
        if value and isinstance(value, Doc):
            return value.serialized()
        elif value and isinstance(value, ObjectId):
            return value
        return None

    def populate(self, value, next_path):
        r = value
        if isinstance(value, (tuple, list)):
            r = Docs.factory(value[1], value[0])
        if next_path:
            assert isinstance(r, Doc)
            r.populate(next_path)
        return r


class FieldDoc(FieldSpec):

    def __init__(self, doc_class_or_collection_name, **kwargs):
        if isinstance(doc_class_or_collection_name, tuple):
            raise ValueError('FieldDoc only accept single document type')
        self.doc_class_or_collection_name = doc_class_or_collection_name
        self.doc_class = None
        super(FieldDoc, self).__init__((ObjectId, Doc), **kwargs)

    def to_document(self, value):
        if value and isinstance(value, self.doc_clz()):
            return value.object_id
        elif value and isinstance(value, ObjectId):
            return value
        return None

    def from_document(self, oid):
        return oid

    def from_serialized(self, oid):
        return oid and ObjectId(oid)

    def to_serialized(self, value):
        if value and isinstance(value, self.doc_clz()):
            return value.serialized()
        elif value and isinstance(value, ObjectId):
            return value
        return None

    def populate(self, value, next_path):
        r = value
        if r is None:
            return r

        # populate self first.
        if isinstance(value, ObjectId):
            r = Docs.factory(self.doc_clz().manager.collection_name, value)

        # try to populate next_path
        if next_path:
            assert isinstance(r, self.doc_clz())
            r.populate(next_path)
        return r

    def doc_clz(self):
        """
        sanitize self.doc_class to be Document class object. (if it was given as string)
        :return: document class object,
        """
        if self.doc_class is None:
            if isinstance(self.doc_class_or_collection_name, basestring):
                # resolve it to class instead
                self.doc_class = Docs.installed[self.doc_class_or_collection_name]
                if self.doc_class is None:
                    raise ValueError('Unknown doc_class %s' % self.doc_class_or_collection_name)
            else:
                self.doc_class = self.doc_class_or_collection_name
            if not issubclass(self.doc_class, Doc):
                raise ValueError('Expected doc_class to be subclass of Doc')
        return self.doc_class


class FieldList(FieldSpec):

    def __init__(self, element_fieldspec, **kwargs):
        if not isinstance(element_fieldspec, FieldSpec):
            raise ValueError('element_fieldspec must be FieldSpec instance')
        validators = {
            'default': [],
            'validators': [
                self._validate_element
            ] + kwargs.get('validators', [])
        }
        kwargs.update(validators)
        self.element_fieldspecs = element_fieldspec
        self.remove_none_values = kwargs.pop('remove_none_values', False)
        super(FieldList, self).__init__((tuple, list), **kwargs)

    def to_document(self, value):
        if value is None:
            return []
        return map(lambda v: self.element_fieldspecs.to_document(v), value)

    def from_document(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise DocumentValidationError('value %s is not list' % value)
        return map(lambda v: self.element_fieldspecs.from_document(v), value)

    def from_serialized(self, value):
        if value is None:
            return []
        v = map(lambda v: self.element_fieldspecs.from_serialized(v), value)
        if self.remove_none_values:
            v = filter(lambda v: v is not None, v)
        return v

    def to_serialized(self, value):
        if value is None:
            return []
        v = map(lambda v: self.element_fieldspecs.to_serialized(v), value)
        if self.remove_none_values:
            v = filter(lambda v: v is not None, v)
        return v

    def _validate_element(self, value, name):
        # incoming value is sure be tuple or list, so we need to iterate that
        map(lambda v: self.element_fieldspecs.validate(v, name), value)

    def populate(self, value, next_path):
        value = map(lambda v: self.element_fieldspecs.populate(v, next_path), value)
        value = filter(lambda v: v is not None, value)
        return value


class FieldTuple(FieldSpec):

    def __init__(self, *args, **kwargs):
        for a in args:
            if not isinstance(a, FieldSpec):
                raise ValueError('element_fieldspec must be FieldSpec instance')
        kwargs.update({
            'validators': [
                self._validate_element
            ] + kwargs.get('validators', [])
        })
        self.element_fieldspecs = args
        super(FieldTuple, self).__init__((tuple, list), **kwargs)

    def to_document(self, value):
        if value is None:
            return []
        return map(lambda v: self.element_fieldspecs[v[0]].to_document(v[1]), enumerate(value))

    def from_document(self, value):
        if value is None:
            return ()
        if not isinstance(value, list):
            raise DocumentValidationError('Cannot convert to tuple, expected document value as a list, value=%s' % value)
        return tuple(map(lambda v: self.element_fieldspecs[v[0]].from_document(v[1]), enumerate(value)))

    def from_serialized(self, value):
        if value is None:
            return ()
        v = map(lambda v: self.element_fieldspecs[v[0]].from_serialized(v[1]), enumerate(value))
        return v

    def to_serialized(self, value):
        if value is None:
            return []
        v = map(lambda v: self.element_fieldspecs[v[0]].to_serialized(v[1]), enumerate(value))
        return v

    def _validate_element(self, value, name):
        if len(value) != len(self.element_fieldspecs):
            raise FieldValidationError('FieldSpecTuple expected tuple size=%s' % len(self.element_fieldspecs))

        if value is None:
            return []
        # incoming value is sure be tuple or list, so we need to iterate that
        map(lambda v: self.element_fieldspecs[v[0]].validate(v[1], name), enumerate(value))


class FieldDict(FieldSpec):
    """
    Write and Read as exactly as provided.
    """

    def __init__(self, **kwargs):
        super(FieldDict, self).__init__(dict, **kwargs)


class FieldNested(FieldSpec):

    def __init__(self, field_spec_aware_class, **kwargs):
        assert field_spec_aware_class is not None
        assert issubclass(field_spec_aware_class, _FieldSpecAware)
        self.field_spec_aware_class = field_spec_aware_class
        super(FieldNested, self).__init__(FieldSpecAware, **kwargs)

    def from_document(self, raw_document):
        spec_aware = self.field_spec_aware_class()
        spec_aware.inflate(raw_document)
        return spec_aware

    def to_document(self, value):
        if value is not None:
            assert isinstance(value, self.field_spec_aware_class)
            return value.document()
        else:
            spec_aware = self.field_spec_aware_class()
            return spec_aware.document()

    def from_serialized(self, nested_dict):
        spec_aware = self.field_spec_aware_class()
        spec_aware.deserialized(nested_dict)
        return spec_aware

    def to_serialized(self, value):
        if value is not None:
            assert isinstance(value, self.field_spec_aware_class)
            return value.serialized()
        else:
            spec_aware = self.field_spec_aware_class()
            return spec_aware.serialized()

    def populate(self, value, next_path):
        if value is not None:
            assert isinstance(value, self.field_spec_aware_class)
            return value.populate(next_path)
        else:
            spec_aware = self.field_spec_aware_class()
            return spec_aware.populate(next_path)


# Building FieldSpec index from its parent classes, including itself
def _field_specs(clazz):
    def is_field_spec(clz):
        return {key: fs for key, fs in clz.__dict__.iteritems() if isinstance(fs, FieldSpec)}
    mro = inspect.getmro(clazz)
    fields = reduce(lambda x, y: dict(x.items() + is_field_spec(y).items()), reversed(mro), {})
    doc_key_map = dict(map(lambda (x, f): (f.key or x, x), fields.iteritems()))
    return fields, doc_key_map


class _FieldSpecAware(object):

    def __init__(self):
        super(_FieldSpecAware, self).__init__()
        self.__dict__['fields'], self.__dict__['doc_key_map'] = _field_specs(self.__class__)
        self.dox = {}

    def is_field_spec(self, item):
        return item in self.fields

    def field_spec(self, item):
        if self.is_field_spec(item):
            return self.fields[item]
        else:
            return None

    def __getattribute__(self, item):
        r = super(_FieldSpecAware, self).__getattribute__(item)
        if not item.startswith('__') \
                and item not in ['is_field_spec', 'populate', 'field_spec', 'fields', 'dox'] \
                and self.is_field_spec(item):
            fs = self.field_spec(item)
            if item not in self.dox:
                self.dox[item] = copy.deepcopy(fs.default)
            return self.dox.get(item)
        return r

    def __setattr__(self, key, value):
        fs = self.field_spec(key)
        if fs is not None:
            value = fs.from_python(value)
            fs.validate(value, key)
            self.dox[key] = value
            return
        super(_FieldSpecAware, self).__setattr__(key, value)

    def populate(self, path):
        (cp, sp, next_path) = path.partition('.')
        if cp in self.fields:
            fs = self.fields[cp]
            try:
                self.dox[cp] = fs.populate(self.dox.get(cp, fs.default), next_path)
            except:
                print("Populate '%s' failed" % path)
        return self

    def validate(self):
        map(lambda (k, fs): fs.validate(self.dox.get(k, fs.default), k), self.fields.iteritems())

    def document(self):
        """
        Reverse of inflate
        :return:
        """
        write_fields = filter(lambda (k, f): False == f.transient, self.fields.iteritems())
        def proc(key, f):
            value = f.to_document(self.dox.get(key, f.default))
            if value is None and f.omit_if_none:
                return "omitted", value
            return f.key or key, value
        o = dict(map(lambda (k, f): proc(k, f), write_fields))
        if "omitted" in o:
            del o["omitted"]
        return o

    def inflate(self, raw_document):
        """
        Reverse of document()
        :param document: nested dictionary from database
        :return:
        """
        if raw_document is not None and isinstance(raw_document, dict):
            def bypass(document_key, value, error_policy='print'):
                """
                Assign value directly to dox dict, skip validation process
                :param key:
                :param value:
                :return:
                """
                # Skip reserved keywords
                if document_key in ['_subtype']:
                    return
                if document_key not in self.doc_key_map:
                    if error_policy == 'raise':
                        raise ValueError('%s is not FieldSpec' % document_key)
                    else:
                        print "\t'%s' is not FieldSpec and ignored" % document_key
                        return
                key = self.doc_key_map[document_key]
                fs = self.field_spec(key)
                if fs is not None:
                    # Only save value to dox, if value is not None
                    if value is not None:
                        self.dox[key] = fs.from_document(value)
                        return

            map(lambda (k, v): bypass(k, v), raw_document.iteritems())

    def serialized(self):
        return dict(map(lambda (k, f): (f.key or k, f.to_serialized(self.dox.get(k, f.default))), self.fields.iteritems()))

    def deserialized(self, serialized):
        """
        Reverse of document()
        :param serialized: nested dictionary from database
        :return:
        """
        if serialized is not None and isinstance(serialized, dict):
            def deserialized(document_key, value):
                key = self.doc_key_map[document_key]
                fs = self.field_spec(key)
                if fs is not None:
                    if value is None and fs.is_required() and fs.default is None:
                        raise ValueError("Key %s is supplied, and is required field, but value is none" % document_key)
                    self.__setattr__(key, fs.from_serialized(value or fs.default))
                else:
                    print "%s is not FieldSpec and ignored by deserialized" % key
            map(lambda (k, v): deserialized(k, v), serialized.iteritems())


class _FieldSpecAwareMetaClass(type):
    def __new__(cls, clsname, bases, dct):
        meta = 'Meta' in dct and dct['Meta'].__dict__ or {}
        # register myself to Doc repository
        if 'collection_name' in meta:
            collection_name = meta['collection_name']
            connection_name = meta['connection_name'] if 'connection_name' in meta else 'default'

            if re.compile('^:').match(collection_name):
                # find "first" parent class with manager
                parent_collection_name = next((x.manager.collection_name for x in bases if hasattr(x, 'manager')), None)
                if parent_collection_name is None:
                    raise DeveloperFault("Unable to extend empty non-discoverable parent class")
                collection_name = "%s%s" % (parent_collection_name, collection_name)

            dct['manager'] = Docs(collection_name, connection_name=connection_name)
            clx = super(_FieldSpecAwareMetaClass, cls).__new__(cls, clsname, bases, dct)
            # Register indexing see:
            # http://api.mongodb.org/python/current/api/pymongo/collection.html#pymongo.collection.Collection.create_index
            Docs.register(clx, meta['indices'] if 'indices' in meta else [])
            # Permission registration
            # default = meta.pop("require_permission", False)
            # define_permission(collection_name,
            #                   read=meta.pop('permission_read', default),
            #                   write=meta.pop('permission_write', default),
            #                   delete=meta.pop('permission_delete', default))

            print "FieldSpecAware \"%s\" is created and discoverable via \"%s\"" % (clsname, collection_name)
        else:
            clx = super(_FieldSpecAwareMetaClass, cls).__new__(cls, clsname, bases, dct)
            print "FieldSpecAware \"%s\" is created." % clsname
        return clx


# Public class
class FieldSpecAware(six.with_metaclass(_FieldSpecAwareMetaClass, _FieldSpecAware)):
    pass


class Doc(FieldSpecAware):
    PERM_W = 'write'
    PERM_R = 'read'
    PERM_D = 'delete'
    object_id = FieldObjectId(key="_id")

    def __init__(self, object_id=None):
        super(Doc, self).__init__()
        self.object_id = helper.object_id(object_id)
        self._injected_object_id = None
        self.load()

    def load(self):
        if self.object_id is not None:
            raw = self.manager.o.find_one(self.object_id)
            if not raw:
                raise DocumentValidationError(_('Failed to load document, unknown document_id=%s' % self.object_id))
            self.inflate(raw)
        else:
            self._injected_object_id = ObjectId()
            self.object_id = self._injected_object_id

    def is_new(self):
        return self._injected_object_id is not None and self.object_id == self._injected_object_id

    def save(self):
        self.validate()
        self.object_id = self.manager.write(self.document())
        self._injected_object_id = None     # ObjectId has been committed.
        return self.object_id

    def invoke(self, user, requested_operation):
        """
        Custom model operation exeuction, allow remote execution.

        :param requested_operation: (String)
        :return: self, facilitate pipeline operations
        """
        method, parameter = requested_operation.split(" ", 1)
        self.__class__.__dict__['invoke_%s' % method](self, user, parameter)
        return self

    def assert_permission(self, user, action, *args):
        if self.manager.collection_name is None:
            raise DeveloperFault(_("Unable to check permission against non-modeled document"))
        user.can("%s+%s" % (self.manager.collection_name, action), args[0] if len(args) > 0 else None, True)

    def __eq__(self, other):
        if issubclass(other.__class__, self.__class__):
            return self.object_id == other.object_id
        return False


class Validatable(Doc):

    def __init__(self, objectid=None):
        super(Validatable, self).__init__(objectid)
        self.validation_errors = []

    def validate_data(self, throw=True, **kwargs):
        self.validation_errors = self.validate_for_errors(**kwargs)
        if throw and any(len(errs) > 0 for errs in self.validation_errors):
            raise DocumentValidationError(self.validation_errors)
        return self

    def validate_for_errors(self, **kwargs):
        return [["Validatable required validate_for_error to be implemented"]]

    def serialized(self):
        o = super(Validatable, self).serialized()
        o["errors"] = self.validation_errors
        return o