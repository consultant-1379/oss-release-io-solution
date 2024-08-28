"""
A mock of the response class from requests module
"""
import json


class MockResponse:
    """
    A mock of the object response from a request
    """
    # pylint: disable=too-few-public-methods
    def __init__(self, content, status_code, reason=''):
        self.content = content
        self.status_code = status_code
        self.reason = reason
        self.text = str(content)

    def json(self):
        """
        Converts the content into a dictionary
        :return: json
        :rtype: dict
        """
        return json.loads(self.content)
