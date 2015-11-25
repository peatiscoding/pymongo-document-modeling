from bson import ObjectId
import re


class DictDiffer(object):
    """
    Calculate the difference between two dictionaries as:
    (1) items added
    (2) items removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values
    """
    def __init__(self, current_dict, past_dict):
        self.current_dict, self.past_dict = current_dict, past_dict
        self.set_current, self.set_past = set(current_dict.keys()), set(past_dict.keys())
        self.intersect = self.set_current.intersection(self.set_past)

    def added(self):
        return self.set_current - self.intersect

    def removed(self):
        return self.set_past - self.intersect

    def changed(self):
        return set(o for o in self.intersect if self.past_dict[o] != self.current_dict[o])

    def unchanged(self):
        return set(o for o in self.intersect if self.past_dict[o] == self.current_dict[o])

    def elaborate(self):
        return {
            'added': {k: self.current_dict[k] for k in self.added()},
            'removed': {k: self.past_dict[k] for k in self.removed()},
            'changed': {k: {'from': self.past_dict[k], 'to': self.current_dict[k]} for k in self.changed()}
            }


def object_id(object_id_or_str):
    if object_id_or_str is None:
        return None
    if isinstance(object_id_or_str, basestring):
        return ObjectId(object_id_or_str)
    return object_id_or_str


_object_id_pattern = re.compile(r'[a-zA-Z0-9]{24}')


def is_object_id(object_id_or_str):
    return isinstance(object_id_or_str, ObjectId) or _object_id_pattern.match(object_id_or_str) is not None
