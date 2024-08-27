import unittest
from decimal import Decimal
from unittest.mock import patch
from io import StringIO
from context import microscope
from microscope.controllers.bbd30x import BBD30XController


class TestBBD30XControllerIntegration(unittest.TestCase):

    def setUp(self):
        """Set up the controller for testing."""
        name = 'BBD30X'
        self.conn = BBD30XController(
            name=name, simulated=True, verbose=True, very_verbose=True
        )

    def test_init(self):
        """Test the initialization of the controller."""
        self.assertEqual(self.conn.serial_no, '103251384')
        self.assertEqual(self.conn.name, 'BBD30X')
        self.assertTrue(self.conn.simulated)
        self.assertEqual(len(self.conn.channels), 2)

    @patch('sys.stdout', new_callable=StringIO)
    def test_print_device_info(self, mock_stdout):
        """Test the print_device_info method."""
        self.conn.print_device_info()
        expected = """------------------------
DEVICE: BBD30X
Device Description: BBD30X
Device Serial No: 103251384
Device Type: Controller
Device Hardware Version: Unknown
Device Firmware Version: Unknown
------------------------"""
        self.assertEqual(mock_stdout.getvalue().strip(), expected)

    @patch('sys.stdout', new_callable=StringIO)
    def test_print_channel_info(self, mock_stdout):
        """Test the print_channel_info method."""
        # with patch('builtins.print') as mocked_print:
        #     self.controller.print_channel_info('X')
        #     mocked_print.assert_called()
        self.conn.print_channel_info('X')
        expected = """------------------------
Channel X Info:
Class: <class 'microscope.controllers.bbd30x.SimulatedChannel'>
Channel Description: Simulated Channel 1
Channel Serial No: 1
Channel Type: Simulated Channel
Channel Hardware Version: Simulated Hardware
Channel Firmware Version: Simulated Firmware
------------------------"""
        self.assertEqual(mock_stdout.getvalue().strip(), expected)

    @patch('sys.stdout', new_callable=StringIO)
    def test_print_velocity_params(self, mock_stdout):
        """Test the print_velocity_params method."""
        # with patch('builtins.print') as mocked_print:
        #     self.controller.print_velocity_params(['X'])
        #     mocked_print.assert_called()
        self.conn.print_velocity_params(['X'])
        expected = """------------------------
Channel X Velocity Parameters
Acceleration: 10
MaxVelocity: 20
MinVelocity: 1
------------------------"""
        self.assertEqual(mock_stdout.getvalue().strip(), expected)


if __name__ == '__main__':
    unittest.main()
