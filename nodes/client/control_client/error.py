class ControlError:

    def __init__(self, msg: str, code: int, e: Exception or None):
        self.msg = msg
        self.code = code
        self.exception = e

    def __str__(self):
        return '{}: {}\nexception: {}'.format(self.code, self.msg, self.exception)