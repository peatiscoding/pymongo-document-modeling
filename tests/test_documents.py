from pymongo_document import documents as doc, errors as err, conf
import pymongo
import unittest
from datetime import datetime, timedelta


class SimpleDocument(doc.Doc):
    int_val = doc.FieldNumeric()
    str_val = doc.FieldString(none=False, default="default_value_of_string")

    class Meta:
        collection_name = "simple_document"


class ABitComplexDocument(SimpleDocument):
    int_val_2 = doc.FieldNumeric(none=False)
    str_val = doc.FieldString(default="default_value_changed")

    class Meta:
        collection_name = ":complex_1"  # use ':' to annotate the system that this will share the same collection


class HolderOfSimpleDocuments(doc.Doc):
    list_of_docs = doc.FieldList(doc.FieldDoc(SimpleDocument))

    class Meta:
        collection_name = "document_holders"

# Clean up
SimpleDocument.manager.delete()


class TestDocumentBasic(unittest.TestCase):
    """
    Test Cases
    """

    def test_define_class(self):
        d = SimpleDocument()
        d.save()

        items = SimpleDocument.manager.find({'_id': d.object_id})
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].object_id, d.object_id)
        self.assertEqual(items[0].int_val, None)
        self.assertEqual(items[0].str_val, "default_value_of_string")

        items[0].int_val = 750
        items[0].save()

        item = SimpleDocument(d.object_id)      # Load object using constructor
        self.assertEqual(item.object_id, d.object_id)
        self.assertEqual(item.int_val, 750)
        self.assertEqual(item.str_val, "default_value_of_string")

    def test_document_inheritance(self):
        c = ABitComplexDocument()
        self.assertRaises(err.FieldValidationError, c.save)     # c.int_val_2 is non-nullable integer value must be set

        c.int_val_2 = 300
        c.save()

        cursor = SimpleDocument.manager.find({'_id': c.object_id})
        self.assertEqual(len(cursor), 1)
        self.assertEqual(cursor[0].object_id, c.object_id)
        self.assertEqual(cursor[0].int_val_2, 300)
        self.assertEqual(cursor[0].str_val, "default_value_changed")
        self.assertEqual(cursor[0].int_val, None)        # int_val is inherited

    def test_document_simple_read_write_api(self):
        # Save
        o = SimpleDocument()
        o.int_val = 30
        o.str_val = "string_value"
        o.save()

        # Load
        r = SimpleDocument(o.object_id)
        self.assertEqual(o.int_val, 30)
        self.assertEqual(o.str_val, "string_value")
        self.assertEqual(r.int_val, o.int_val)
        self.assertEqual(r.str_val, o.str_val)

    def test_document_api(self):
        # Make sure everything is clean before we start
        SimpleDocument.manager.delete({'str_val': 'find_me'})

        # Create multiple value of SimpleDocument
        def new_simple_doc(int_val, str_val):
            o = SimpleDocument()
            o.int_val = int_val
            o.str_val = str_val
            o.save()
            return o
        o1 = new_simple_doc(30, 'find_me')
        o2 = new_simple_doc(32, 'find_me')
        o3 = new_simple_doc(31, 'find_me')

        # Test Find API
        found = SimpleDocument.manager.find({
            'str_val': 'find_me',
        }).sort('int_val', pymongo.DESCENDING)
        self.assertEqual(len(found), 3)
        self.assertEqual(found[0].object_id, o2.object_id)
        self.assertEqual(found[1].object_id, o3.object_id)
        self.assertEqual(found[2].object_id, o1.object_id)

        # Find with condition
        found = SimpleDocument.manager.find({
            'str_val': 'find_me',
            'int_val': {'$lt': 31}
        })
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].object_id, o1.object_id)

        # Find with condition using $or
        found = SimpleDocument.manager.find({
            'str_val': 'find_me',
            '$or': [
                {
                    'int_val': {'$gt': 31}
                },
                {
                    'int_val': {'$lt': 31}
                }
            ],
        }).sort('int_val')
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0].object_id, o1.object_id)
        self.assertEqual(found[1].object_id, o2.object_id)

        # Updated value instantly effect the search result.
        o3.int_val = 50
        o3.save()

        # Find with nested condition
        found = SimpleDocument.manager.find({
            'str_val': 'find_me',
            '$or': [
                {
                    'int_val': {'$gt': 31}
                },
                {
                    'int_val': {'$lt': 31}
                }
            ]
        }).sort('int_val')
        self.assertEqual(found[2].object_id, o3.object_id)
        self.assertEqual(found[1].object_id, o2.object_id)
        self.assertEqual(found[0].object_id, o1.object_id)

        # Test Update API, make an update all values by 5.
        SimpleDocument.manager.update(cond={
            'str_val': 'find_me'
        }, update={
            '$inc': {'int_val': 5}
        })

        # Check updated for values
        found = SimpleDocument.manager.find({
            'str_val': 'find_me',
            '$or': [
                {
                    'int_val': {'$lt': 31}
                }
            ],
        }).sort('int_val')
        self.assertEqual(len(found), 0)

        found = SimpleDocument.manager.find({
            'str_val': 'find_me',
        }).sort('int_val')
        self.assertEqual(len(found), 3)
        self.assertEqual(found[0].int_val, 35)
        self.assertEqual(found[1].int_val, 37)
        self.assertEqual(found[2].int_val, 55)

        # Test find API
        # - Using sort
        int_seq = map(lambda o: o.int_val, SimpleDocument.manager.find({'str_val': 'find_me'}).sort('int_val', pymongo.ASCENDING))
        self.assertEqual(int_seq, [35, 37, 55])

        # - Using __getitem__ method
        int_seq = map(lambda o: o.int_val, SimpleDocument.manager.find({'str_val': 'find_me'}).sort('int_val', pymongo.ASCENDING)[:2])
        self.assertEqual(int_seq, [35, 37])

        # Test del API
        found = SimpleDocument.manager.find({
            'str_val': 'find_me'
        })
        self.assertEqual(len(found), 3)

        # - Delete one
        found[0].delete()
        found[1].delete()
        self.assertEqual(len(found), 1)

        # Clean up
        SimpleDocument.manager.delete({'str_val': 'find_me'})

    def test_list_field(self):
        s = SimpleDocument()
        s.str_val = "500"
        s.int_val = 500
        s.save()

        c = ABitComplexDocument()
        c.int_val_2 = 1250
        c.int_val = 30
        c.str_val = "123"
        c.save()

        l = HolderOfSimpleDocuments()
        l.list_of_docs.append(s)
        l.list_of_docs.append(c)
        l.save()

        # load document with object_id
        o = HolderOfSimpleDocuments(l.object_id)
        self.assertEqual(o.object_id, l.object_id)
        self.assertEqual(len(o.list_of_docs), 2)
        self.assertFalse(c in o.list_of_docs)
        self.assertTrue(c.object_id in o.list_of_docs)
        o.populate('list_of_docs')
        self.assertTrue(c in o.list_of_docs)
        self.assertTrue(s in o.list_of_docs)

        # Check BUG:
        #   List default value inherit through multiple instance
        n = HolderOfSimpleDocuments()
        self.assertEqual(len(n.list_of_docs), 0)

    def test_object_id_field(self):

        class D(doc.Doc):
            oid = doc.FieldObjectId(none=False)

            class Meta:
                collection_name = 'test_doc'

        o = D()

        def wrongly_assigned():
            o.object_id = 3

        self.assertRaises(err.FieldValidationError, wrongly_assigned)   # Unable to assign incorrect data type
        self.assertRaises(err.FieldValidationError, o.save)             # oid is required.

        def wrong_data_type_assigned():
            o.oid = str(doc.FieldObjectId.new_id())

        self.assertRaises(err.FieldValidationError, wrong_data_type_assigned)   # Need to be ObjectId only.

        o.oid = doc.FieldObjectId.new_id()
        o.save()

        r = D(o.object_id)
        self.assertEqual(r.object_id, o.object_id)
        self.assertEqual(r.oid, o.oid)

    def test_dict_field(self):
        class DictFieldDocument(doc.Doc):
            data = doc.FieldDict(none=False)

            class Meta:
                collection_name = 'test_doc2'

        o = DictFieldDocument()
        o.data = {
            'this': 'is a new value',
            'that': {
                'is': {
                    'nested': ['array', 'of', 'value']
                },
                'or': [
                    {
                        'a': 40,
                        'b': 50,
                        'c': 60,
                        'd': [1, 2, 3, {'val': 55}]
                    }
                ]
            }
        }
        o.save()

        r = DictFieldDocument(o.object_id)
        self.assertEqual(r.object_id, o.object_id)
        self.assertEqual(r.data, o.data)
        self.assertEqual(r.data['that']['or'][0]['d'][3]['val'], 55)

    def test_nested_field(self):
        class NestedContentDocument(doc.FieldSpecAware):
            int_val = doc.FieldNumeric(default=303)
            str_val = doc.FieldString(default="default_value")

        class NestedFieldDocument(doc.Doc):
            content = doc.FieldNested(NestedContentDocument)

            class Meta:
                collection_name = 'test_doc3'

        o = NestedFieldDocument()
        o.content = NestedContentDocument()
        o.content.int_val = 500
        o.save()

        r = NestedFieldDocument(o.object_id)
        self.assertEqual(r.content.int_val, 500)
        self.assertEqual(r.content.str_val, "default_value")

    def test_string_field(self):
        def define_bad_class():
            class StringDocument(doc.Doc):
                str = doc.FieldString(max_length=5, fixed_length=3)

                class Meta:
                    collection_name = 'create_me_if_you_can'
        self.assertRaises(err.DeveloperFault, define_bad_class)

        class StringDocument(doc.Doc):
            str = doc.FieldString(max_length=10)
            str_fixed = doc.FieldString(fixed_length=14)
            str_required = doc.FieldString(none=False)
            str_defaulted = doc.FieldString(default="new_default_value")
            str_patterned = doc.FieldString(pattern=r'[a-z]\d{3}')

            class Meta:
                collection_name = 'test_doc_string'
        o = StringDocument()

        def assign_bad_value():
            o.str = "this is too long string value"
        self.assertRaises(err.FieldValidationError, assign_bad_value)
        o.str = "short val"

        def assign_too_short_value():
            o.str_fixed = "too short"
        self.assertRaises(err.FieldValidationError, assign_too_short_value)

        def assign_too_long_value():
            o.str_fixed = "too looooonnnng"
        self.assertRaises(err.FieldValidationError, assign_too_long_value)
        o.str_fixed = "balanced value"

        def assign_wrong_pattern_value(val):
            o.str_patterned = val
        self.assertRaises(err.FieldValidationError, lambda: assign_wrong_pattern_value(1345))
        self.assertRaises(err.FieldValidationError, lambda: assign_wrong_pattern_value('3a53'))
        self.assertRaises(err.FieldValidationError, lambda: assign_wrong_pattern_value('3413'))
        self.assertRaises(err.FieldValidationError, lambda: assign_wrong_pattern_value('A350'))
        o.str_patterned = 'z350'
        o.str_patterned = 'd591'
        o.str_patterned = 'b999'

        self.assertRaises(err.FieldValidationError, lambda: o.save())   # str_required is required

        o.str_required = "some_value"
        o.save()

        r = StringDocument(o.object_id)
        self.assertEqual(r.object_id, o.object_id)
        self.assertEqual(o.str, "short val")
        self.assertEqual(o.str_required, "some_value")
        self.assertEqual(o.str_fixed, "balanced value")
        self.assertEqual(o.str_defaulted, "new_default_value")
        self.assertEqual(o.str_patterned, "b999")
        self.assertEqual(r.str, o.str)
        self.assertEqual(r.str_required, o.str_required)
        self.assertEqual(r.str_fixed, o.str_fixed)
        self.assertEqual(r.str_defaulted, o.str_defaulted)
        self.assertEqual(r.str_patterned, o.str_patterned)

    def test_numeric_field(self):
        def define_bad_numeric_class():
            class NumericDocument(doc.Doc):
                number = doc.FieldNumeric(max_value=30, min_value=100)

                class Meta:
                    collection_name = 'create_me_if_you_can'
        self.assertRaises(err.DeveloperFault, define_bad_numeric_class)

        class NumericDocument(doc.Doc):
            VALUE_1 = 1
            VALUE_2 = 2
            VALUE_3 = 3
            NUMBER_4_VALUES = (
                (VALUE_1, '1st value'),
                (VALUE_2, '2nd value'),
                (VALUE_3, '3rd value')
            )
            number1 = doc.FieldNumeric(max_value=30, min_value=10, none=False)
            number2 = doc.FieldNumeric(max_value=30.5, none=False)
            number3 = doc.FieldNumeric(min_value=-15.0, default=17)
            number4 = doc.FieldNumeric(choices=NUMBER_4_VALUES, default=VALUE_1)

            class Meta:
                collection_name = 'test_doc_numeric'

        o = NumericDocument()
        self.assertRaises(err.FieldValidationError, lambda: o.save())

        def assign_wrong_value1():
            o.number1 = 300
        self.assertRaises(err.FieldValidationError, assign_wrong_value1)
        o.number1 = 30      # set at max_value is okay

        def assign_wrong_value2():
            o.number1 = -50
        self.assertRaises(err.FieldValidationError, assign_wrong_value2)
        o.number2 = -50

        def assign_out_of_choice_value(val):
            o.number4 = val
        self.assertRaises(err.FieldValidationError, lambda: assign_out_of_choice_value(5))
        self.assertRaises(err.FieldValidationError, lambda: assign_out_of_choice_value(-1))
        self.assertRaises(err.FieldValidationError, lambda: assign_out_of_choice_value(0))
        self.assertRaises(err.FieldValidationError, lambda: assign_out_of_choice_value(4.4))
        self.assertRaises(err.FieldValidationError, lambda: assign_out_of_choice_value(3.2))
        self.assertRaises(err.FieldValidationError, lambda: assign_out_of_choice_value(2.5))
        o.number4 = NumericDocument.VALUE_2
        o.save()

        r = NumericDocument(o.object_id)
        self.assertEqual(o.number1, 30)
        self.assertEqual(o.number2, -50)
        self.assertEqual(o.number3, 17)
        self.assertEqual(o.number4, NumericDocument.VALUE_2)
        self.assertEqual(r.number1, o.number1)
        self.assertEqual(r.number2, o.number2)
        self.assertEqual(r.number3, o.number3)
        self.assertEqual(r.number4, o.number4)

    def test_validation_field(self):
        def define_bad_validation_field_document():
            class BadValidationField(doc.Doc):
                bad_validation_field = doc.FieldNumeric(validators='simple_string')

                class Meta:
                    collection_name = 'create_me_if_you_can'

        self.assertRaises(err.DeveloperFault, define_bad_validation_field_document)

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
            custom_value = doc.FieldDateTime(validators=[in_the_past_or_throw])

            class Meta:
                collection_name = 'test_me_document'

        o = TestMeDocument()

        def assign_odd_number():
            o.even_number = 31
        self.assertRaises(err.FieldValidationError, assign_odd_number)
        o.even_number = 30

        def assign_negative_number():
            o.positive_number = -1
        self.assertRaises(err.FieldValidationError, assign_negative_number)
        o.positive_number = 300

        def assign_negative_even_number():
            o.negative_odd_number = -2
        self.assertRaises(err.FieldValidationError, assign_negative_even_number)
        o.negative_odd_number = -3

        def assign_future_value_date():
            o.custom_value = datetime.now() + timedelta(days=1)
        self.assertRaises(err.FieldValidationError, assign_future_value_date)
        o.custom_value = datetime.now() - timedelta(days=1)

    def test_tuple_field(self):
        class TupleDocument(doc.Doc):
            tuple_field = doc.FieldTuple(doc.FieldNumeric(validators=[(lambda v: v <= 5, 'Value must be more than 5')]),
                                         doc.FieldString(),
                                         doc.FieldNumeric(none=False),
                                         doc.FieldNumeric(none=True))

            class Meta:
                collection_name = 'test_tuple_document'

        o = TupleDocument()

        # Test Assign Bad Values to tuple
        def assign_bad_values():
            o.tuple_field = (12, 'test', None, 12)
        self.assertRaises(doc.FieldValidationError, assign_bad_values)

        def assign_bad_values2():
            o.tuple_field = (5, 'test', 50, None)
        self.assertRaises(doc.FieldValidationError, assign_bad_values2)

        # Assign good value
        o.tuple_field = (12, 'test', 50, None)
        o.save()

        # Test loading
        l = TupleDocument(o.object_id)
        self.assertEqual(l.tuple_field, o.tuple_field)

    def test_connections(self):
        def define_bad_connection_class():
            class BadConnectionName(doc.Doc):
                useless_field = doc.FieldNumeric()

                class Meta:
                    collection_name = 'create_me_if_you_can'
                    connection_name = 'bad_connection_name'

        self.assertRaises(err.DeveloperFault, define_bad_connection_class)

        def define_non_exist_connection_class():
            class BadConnectionName(doc.Doc):
                useless_field = doc.FieldNumeric()

                class Meta:
                    collection_name = 'create_me_if_you_can'
                    connection_name = 'test_data_pool'

        self.assertRaises(err.DeveloperFault, define_non_exist_connection_class)

        conf.update_config('tests')
        define_non_exist_connection_class()

        self.assertRaises(err.DeveloperFault, lambda: conf.update_config('tests/unknown_config_file.ini'))
        self.assertRaises(err.DeveloperFault, lambda: conf.update_config('tests/conf/'))

if __name__ == '__main__':
    unittest.main()
