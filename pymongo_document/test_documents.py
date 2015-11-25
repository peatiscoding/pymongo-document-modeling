from pymongo_document import documents as doc
import unittest


class TestDocumentBasic(unittest.TestCase):

    def test_class_define(self):

        class SimpleDocument(doc.Doc):
            int_val = doc.FieldNumeric()
            str_val = doc.FieldString(default="default_value_of_string")

            class Meta:
                collection_name = "simple_document"

        d = SimpleDocument()
        d.save()

        items = SimpleDocument.manager.find(cond={'_id': d.object_id})
        self.assertEqual(len(items), 1)
        self.assertEqual(d.object_id, items[0].object_id)


if __name__ == '__main__':
    unittest.main()
