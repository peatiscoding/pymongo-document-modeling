
class DeveloperFault(Exception):

    def __init__(self, *args, **kwargs):
        super(DeveloperFault, self).__init__(*args, **kwargs)


class DocumentValidationError(Exception):

    def __init__(self, *args, **kwargs):
        super(DocumentValidationError, self).__init__(*args, **kwargs)


class FieldValidationError(Exception):

    def __init__(self, value, message, name="No name"):
        super(FieldValidationError, self).__init__("Field \"%s\" value=\"%s\" type=\"%s\" message=\"%s\""
                                                   % (name, value, type(value), message))
