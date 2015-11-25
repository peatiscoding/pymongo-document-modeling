import datetime
import documents as doc
from errors import DeveloperFault


class RunningNumberPolicy(object):
    """
    Abstract class: RunningNumberPolicy

    Calculate and format the value, reset the next_value of rnc is necessary.
    """
    def next(self, rnc):
        r = rnc.next_value
        rnc.next_value = rnc.next_value + 1
        rnc.save()
        return r


class MonthlyRunningNumberPolicy(RunningNumberPolicy):

    prefix = None

    def __init__(self, prefix=None):
        self.prefix = prefix

    def next(self, rnc):
        today_threshold = int('{:%Y%m}'.format(datetime.datetime.today())) * 10000
        if rnc.next_value < today_threshold:
            rnc.next_value = today_threshold

        new_number = str(super(MonthlyRunningNumberPolicy, self).next(rnc))
        return self.prefix + new_number if self.prefix else new_number


class DailyRunningNumberPolicy(RunningNumberPolicy):

    prefix = None

    def __init__(self, prefix=None):
        self.prefix = prefix

    def next(self, rnc):
        today_threshold = int('{:%Y%m%d}'.format(datetime.datetime.today())) * 10000
        if rnc.next_value < today_threshold:
            rnc.next_value = today_threshold

        new_number = str(super(DailyRunningNumberPolicy, self).next(rnc))
        return self.prefix + new_number if self.prefix else new_number


class RunningNumberCenter(doc.Doc):
    """
    Policy, such batch number will be created, and assumed that the number
    will be successfully consumed by next process.
    :return: new batch number obeys format: YYYYMMDD#####
    """
    policies = {}
    name = doc.FieldString(none=False)
    next_value = doc.FieldNumeric(default=1)

    def __init__(self, object_id=None):
        super(RunningNumberCenter, self).__init__(object_id)

    @staticmethod
    def new_number(key):
        if key not in RunningNumberCenter.policies:
            raise DeveloperFault("%s key is not recognized in RunningNumberPolicy" % key)

        policy = RunningNumberCenter.policies[key]
        pair = RunningNumberCenter.manager.find(cond={'name': key})
        if len(pair) == 0:
            o = RunningNumberCenter()
            o.name = key
            o.save()
            pair.append(o)

        # proceed to next number
        return policy.next(pair[0])

    @staticmethod
    def register_policy(key, policy):
        RunningNumberCenter.policies[key] = policy

    class Meta:
        collection_name = '_number-center'