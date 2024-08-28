"""
Contains exceptions used in OSS release IO solution
"""


class ShellExecutionException(Exception):
    """Shell Execution Exception"""
    def __init__(self, message=None):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        if self.message:
            return f'Shell Execution Exception, {self.message} '
        return 'Shell Execution Exception has been raised'


class ConfigNotFoundException(Exception):
    """Config Not Found Exception"""
    def __init__(self, message=None):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        if self.message:
            return f'Config Not Found, {self.message} '
        return 'Config Not Found has been raised'
