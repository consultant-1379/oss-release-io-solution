"""This module contains configuration functions."""


from configparser import ConfigParser
from os.path import expanduser, join, dirname


# pylint: disable=too-many-ancestors
class ApplicationConfig(ConfigParser):
    """
    A class to read the application.ini files to retrieve project settings.

    This class extends the SafeConfigParser
    and preruns the read function so that it
    first reads the packages application.ini, followed
    by a users application.ini in their home directory
    """

    def __init__(self):
        """Initialize a ApplicationConfig object."""
        super(ApplicationConfig, self).__init__()
        self.read([
            join(dirname(__file__), 'etc/application.ini'),
            expanduser('~/.application.ini')
        ], encoding=None)
