""" Tests the blaziken.utils package. """
# Meta imports
from __future__ import annotations
# Built-in imports
from unittest import TestCase
from unittest.mock import MagicMock
# Project imports
from blaziken import utils
from blaziken.exceptions import RequestError
from blaziken.exceptions import ResponseError


class UtilsTests(TestCase):

    # region valid_bucket_name() tests
    def test_valid_bucket_name__valid_name__success(self):
        """ Tests that valid names are accepted. """
        self.assertTrue(utils.valid_bucket_name('123456'), "Name must have at least 6 chars")
        self.assertTrue(utils.valid_bucket_name('a' * 50), "Name must have at most 50 chars")
        self.assertTrue(utils.valid_bucket_name('hello-world'),
                        "Name must contain only letters, numbers and dashes -")

    def test_valid_bucket_name__valid_name__failure(self):
        """ Tests that valid names are accepted. """
        self.assertFalse(utils.valid_bucket_name('12345'), "Fails on names with less than 6 chars")
        self.assertFalse(utils.valid_bucket_name('a' * 51), "Fails on names with more than 50 char")
        self.assertFalse(utils.valid_bucket_name('b2-bucket'), "Fails on names with the b2- prefix")
        invalid_chars = "Fails on names that contains chars other than letters, numbers or dashes -"
        self.assertFalse(utils.valid_bucket_name('hello world'), invalid_chars)
        self.assertFalse(utils.valid_bucket_name('hello_world'), invalid_chars)
        self.assertFalse(utils.valid_bucket_name('!@#$%¨&*)(_[]'), invalid_chars)
    # endregion

    # region check_response_error() tests
    def test_check_response_error__valid_response__nothing_happens(self):
        """ The check_response_error() does nothing if no error is found. """
        response = MagicMock()
        response.status_code = 200
        self.assertIsNone(utils.check_response_error(response))

    def test_check_response_error__invalid_response__raises_response_error(self):
        """ The check_response_error() raises a RequestError if an error is found. """
        response = MagicMock()
        response.status_code = 400
        response.text = '{"message": "foo", "code": 1, "status": 400}'
        self.assertRaises(RequestError, utils.check_response_error, response)
    # endregion

    # region check_b2_errors() tests
    def test_check_b2_errors__valid_response__nothing_happens(self):
        """ The check_b2_errors() does nothing if no error is found. """
        data = {'status': 200}
        self.assertIsNone(utils.check_b2_errors(data, ''))

    def test_check_b2_errors__invalid_response__raises_response_error(self):
        """ The check_b2_errors() raises a RequestError if an error is found. """
        data = {'status': 400}
        message = 'error raised'
        try:
            utils.check_b2_errors(data, message)
        except ResponseError as error:
            self.assertEqual(str(error), message)
    # endregion
