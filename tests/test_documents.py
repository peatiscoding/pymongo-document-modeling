from pymongo_document import documents as doc
from pymongo_document import errors as err
import unittest


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


class TestDocumentBasic(unittest.TestCase):

    def test_class_define(self):
        d = SimpleDocument()
        d.save()

        items = SimpleDocument.manager.find(cond={'_id': d.object_id})
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

    def test_class_inheritance(self):
        c = ABitComplexDocument()
        self.assertRaises(err.FieldValidationError, c.save)     # c.int_val_2 is non-nullable integer value must be set

        c.int_val_2 = 300
        c.save()

        l = SimpleDocument.manager.find(cond={'_id': c.object_id})
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0].object_id, c.object_id)
        self.assertEqual(l[0].int_val_2, 300)
        self.assertEqual(l[0].str_val, "default_value_changed")
        self.assertEqual(l[0].int_val, None)        # int_val is inherited

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

    def test_connections(self):
        thrown = False
        try:
            class BadConnectionName(doc.Doc):
                useless_field = doc.FieldNumeric()

                class Meta:
                    collection_name = 'create_me_if_you_can'
                    connection_name = 'bad_connection_name'
        except err.DeveloperFault:
            thrown = True

        self.assertTrue(thrown)

if __name__ == '__main__':
    unittest.main()
