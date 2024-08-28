"""
This module allows a user to attempt to make a request multiple times if the target host is
temporarily down
"""

import logging
import time
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# pylint: disable=no-member, too-many-arguments
def request_retry(type_of_request, url, max_retry, body=None, headers=None, auth=None, proxy=None, ssl=False):
    """
    Function to retry requests if the target host is not found. Geometric retry is used here.
    :param type_of_request: Which REST request is being conducted
    :param url: URL you want to run your request against
    :param max_retry: Amount of times to retry the request
    :param body: The payload which will be sent in the request body
    :param auth: Basic Authentication credentials for the request
    :param proxy: Proxy dict if you would like to route request through proxy
    :param ssl: Should be set to True if you want to enable SSL verification.
    :return: response
    :rtype: requests.Response
    """
    count = 0
    response = None
    valid_response_codes = [requests.codes.ok, requests.codes.created]
    logging.debug(f"type_of_request: {str(type_of_request)}")
    logging.debug(f"url: {str(url)}")
    while count < max_retry:
        try:
            response = make_request_based_on_input(type_of_request, url, body, headers, auth, proxy, ssl)
            if response and response.status_code in valid_response_codes:
                break
            raise requests.exceptions.RequestException
        except requests.exceptions.RequestException:
            logging.error(f"Could not make the {type_of_request} request")
            if response is not None:
                logging.error(f"Response status code: {str(response.status_code)}")
                logging.error(f"Response reason: {str(response.reason)}")
                logging.error(f"Response output: {str(response.text)}")

                if response.status_code == requests.codes.bad_request:
                    raise Exception("Bad request detected. It is possible you may be missing "
                                    "required information in your request. Please see above.") \
                        from requests.exceptions.RequestException
        count += 1
        if count == max_retry:
            raise Exception(f"Failed to execute {type_of_request} request after {max_retry} tries.")

        logging.warning(f"Failed to make {type_of_request} request. "
                        f"Sleeping and then trying again...")
        time.sleep(2 ** count)
    return response


def make_request_based_on_input(request_type, url, body, headers, auth, proxy, ssl):
    """
    Makes a request based on the request type passed in
    :param request_type: Which REST request is being conducted
    :param url: URL you want to run your request against
    :param body: The payload which will be sent in the request body
    :param proxy: Proxy dict if you would like to route request through proxy
    :return: response
    :rtype: requests.Response
    """
    logging.debug(f"Trying to make {request_type} request")
    response = None
    try:
        if request_type == "GET":
            logging.debug("Doing a GET request")
            response = requests.get(url, headers=headers, proxies=proxy, timeout=5, verify=ssl, auth=auth)
        elif request_type == "PATCH":
            logging.debug("Doing a PATCH request")
            response = requests.patch(url, json=body, headers=headers, timeout=20, proxies=proxy, verify=ssl, auth=auth)
        elif request_type == "PUT":
            logging.debug("Doing a PUT request")
            response = requests.put(url, json=body, headers=headers, timeout=5, proxies=proxy, verify=ssl, auth=auth)
        elif request_type == "POST":
            logging.debug("Doing a POST request")
            response = requests.post(url, json=body, headers=headers, timeout=20, proxies=proxy, verify=ssl, auth=auth)
        elif request_type == "DELETE":
            logging.debug("Doing a DELETE request")
            response = requests.delete(url, headers=headers, timeout=10, proxies=proxy, verify=ssl, auth=auth)
        else:
            raise Exception(f"Unsupported type of request: {request_type}")
    except (requests.exceptions.ProxyError, AssertionError):
        logging.error(f"Could not make {request_type} request due to a Proxy Error")
    return response
