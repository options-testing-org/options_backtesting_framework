
class InvalidAssignmentError(Exception):

    def __init__(self, field_name: str, assignment_type: str):
        self.field_name = field_name
        if assignment_type == "contract":
            self.message = f'Cannot assign value after object is created: {field_name}'
        if assignment_type == "quote":
            self.message = f'Use the "update" method to assign a value to this field: {field_name}'

        super().__init__(self.message)
