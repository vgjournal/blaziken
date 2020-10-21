from unittest import TestCase
from unittest.mock import patch
from unittest.mock import MagicMock

from blaziken import BackBlazeB2


class ApiTests(TestCase):

    account_id = 'test-account-id'
    app_key = 'test-applicationKey'

    def setUp(self):
        """ Sets up the BackBlazeB2 mock that nearly all methods use. """
        self.patcher = patch('blaziken.models.BackBlazeB2')
        self.mock_blaze = self.patcher.start()
        self.mock_api = MagicMock()
        self.mock_blaze.return_value = self.mock_api
        self.addCleanup(self.patcher.stop)


class KeyTests(TestCase):
    """ Test methods related to key management. """

    def setUp(self):
        """ Sets up the BackBlazeB2 mock that nearly all methods use. """
        self.patcher = patch('blaziken.models.BackBlazeB2')
        self.mock_blaze = self.patcher.start()
        self.mock_api = MagicMock()
        self.mock_blaze.return_value = self.mock_api
        self.addCleanup(self.patcher.stop)
