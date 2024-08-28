"""
Unit tests for request_retry.py
"""
import pytest
import requests

from oris.src.etc import request_retry
from oris.tests.unit_tests.mock_response import MockResponse


# pylint: disable=no-self-use
class TestRequestRetry:
    """
    Class to run unit tests for request_retry.py
    """

    def test_make_request_based_on_input_proxy_error(self, monkeypatch):
        """
        Tests that we handle a proxy error
        :param monkeypatch:
        """
        def get_request_mock(url, **kwargs):
            """
            A mock for the get request
            :param url:
            :param kwargs:
            :return: Mock Response
            :rtype: MockResponse
            """
            raise requests.exceptions.ProxyError

        monkeypatch.setattr(requests, "get", get_request_mock)
        actual_response = request_retry.make_request_based_on_input('GET', 'some_url', None, None, None, None, False)
        assert actual_response is None

    def test_make_request_based_on_input_with_incorrect_request_type(self):
        """
        Tests that we handle an invalid request type
        """
        with pytest.raises(Exception) as exception:
            request_retry.make_request_based_on_input('INVALID', 'some_url', None, None, None, None, False)
        expected_exception_value = 'Unsupported type of request: INVALID'
        assert str(exception.value) == expected_exception_value

    def test_make_request_based_on_input_valid(self, monkeypatch):
        """
        Tests that we can make a request successfully
        :param monkeypatch:
        """
        valid_content = {
            "app": "ORIS"
        }

        # pylint: disable=unused-argument
        def request_mock(url, **kwargs):
            """
            A mock for a successful request
            :param url:
            :param kwargs:
            :return: Mock Response
            :rtype: MockResponse
            """
            nonlocal valid_content
            return MockResponse(valid_content, 200)

        request_types = ['GET', 'PATCH', 'PUT', 'POST', 'DELETE']
        for request_type in request_types:
            monkeypatch.setattr(requests, request_type.lower(), request_mock)
            actual_response = \
                request_retry.make_request_based_on_input(request_type, 'some_url', None, None, None, None, False)
            assert actual_response.content == valid_content

    def test_make_request_based_on_input_invalid(self, monkeypatch):
        """
        Tests that we can handle the scenario where a request is unsuccessful
        :param monkeypatch:
        """

        # pylint: disable=unused-argument
        def request_mock(url, **kwargs):
            """
            A mock for an unsuccessful request
            :param url:
            :param kwargs:
            :return: Mock Response
            :rtype: MockResponse
            """
            return MockResponse('', 500)

        request_types = ['GET', 'PATCH', 'PUT', 'POST', 'DELETE']
        for request_type in request_types:
            monkeypatch.setattr(requests, request_type.lower(), request_mock)
            actual_response = request_retry\
                .make_request_based_on_input(request_type, 'some_url', None, None, None, None, False)
            assert actual_response.status_code == 500

    def test_request_retry_valid(self, monkeypatch):
        """
        Tests that we can make a request successfully
        :param monkeypatch:
        """
        valid_content = {
            "app": "ORIS"
        }

        # pylint: disable=unused-argument
        def request_mock(*args):
            """
            A mock for a successful request
            :param args:
            :return: Mock Response
            :rtype: MockResponse
            """
            nonlocal valid_content
            return MockResponse(valid_content, 200)

        monkeypatch.setattr(request_retry, 'make_request_based_on_input', request_mock)
        actual_response = request_retry.request_retry('GET', 'some_url', 1)
        assert actual_response.content == valid_content

    def test_request_invalid(self, monkeypatch):
        """
        Tests that we can handle the scenario where a request is unsuccessful
        :param monkeypatch:
        """
        # pylint: disable=unused-argument
        def request_mock(*args):
            """
            A mock for an unsuccessful request
            :param args:
            :return: Mock Response
            :rtype: MockResponse
            """
            return MockResponse('', 500)

        monkeypatch.setattr(request_retry, 'make_request_based_on_input', request_mock)
        with pytest.raises(Exception) as exception:
            request_retry.request_retry('GET', 'some_url', 1)
        expected_exception_value = \
            'Failed to execute GET request after 1 tries.'
        assert str(exception.value) == expected_exception_value

    def test_request_bad_request(self, monkeypatch):
        """
        Tests that we can handle the scenario where a request returns a "bad request" response.
        :param monkeypatch:
        """
        # pylint: disable=unused-argument
        def request_mock(*args):
            """
            A mock for an unsuccessful request
            :param args:
            :return: Mock Response
            :rtype: MockResponse
            """
            return MockResponse('', 400)

        request_types = ['GET', 'PATCH', 'PUT', 'POST', 'DELETE']
        for request_type in request_types:
            monkeypatch.setattr(request_retry, 'make_request_based_on_input', request_mock)
            with pytest.raises(Exception) as exception:
                request_retry.request_retry(request_type, 'some_url', 1)
            expected_exception_value = 'Bad request detected. It is possible you may be missing ' \
                                       'required information in your request. Please see above.'
            assert str(exception.value) == expected_exception_value
