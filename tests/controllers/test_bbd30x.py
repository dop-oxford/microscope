import unittest
from decimal import Decimal
from unittest.mock import patch
from io import StringIO
from context import microscope
from microscope.controllers.bbd30x import BBD30XController, SimulatedChannel


class TestBBD30XControllerIntegration(unittest.TestCase):

    def setUp(self):
        """Set up the controller for testing."""
        name = 'BBD30X'
        self.conn = BBD30XController(
            name=name, simulated=True, verbose=False, very_verbose=False
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
        self.conn.print_velocity_params(['X'])
        expected = """------------------------
Channel X Velocity Parameters
Acceleration: 10
MaxVelocity: 20
MinVelocity: 1
------------------------"""
        self.assertEqual(mock_stdout.getvalue().strip(), expected)

    def test_decimal_to_float(self):
        """Test the _decimal_to_float method."""
        actual = self.conn._decimal_to_float(Decimal('3.1415'))
        self.assertEqual(actual, 3.1415)

    def test_get_channel_idx(self):
        """Test the _get_channel_idx method."""
        self.assertEqual(self.conn._get_channel_idx('X'), 0)
        self.assertEqual(self.conn._get_channel_idx(2), 1)

    def test_get_channels(self):
        """Test the get_channels method."""
        self.conn.get_channels()
        self.assertIsNotNone(self.conn.channels)

    def test_get_channel_single(self):
        """Test the get_channel_single method."""
        self.conn.get_channel_single('X')
        self.assertIsInstance(self.conn.channels[0], SimulatedChannel)

    def test_load_config_channels(self):
        """Test the load_config_channels method."""
        self.conn.load_config_channels()
        self.assertIsNotNone(self.conn.channels)

    @patch('sys.stdout', new_callable=StringIO)
    def test_load_config_channel_single(self, mock_stdout):
        """Test the load_config_channels method."""
        self.conn.load_config_channel_single('X', verbose=True)
        expected = """Channel X configuration loaded:
None"""
        self.assertEqual(mock_stdout.getvalue().strip(), expected)

    def test_set_setting_channels(self):
        """Test the set_setting_channels method."""
        method = 'microscope.controllers.bbd30x.' + \
            'BBD30XController.set_setting_channel_single'
        with patch(method) as mocked_set:
            self.conn.set_setting_channels('X')
            mocked_set.assert_called()

    def test_set_setting_channel_single(self):
        """Test the set_setting_channel_single method."""
        # Confirm the default settings
        actual = self.conn.channels[0].MotorDeviceSettings
        self.assertEqual(actual, 'Simulated Motor Device Settings')
        # Set new settings
        self.conn.set_setting_channel_single('X', 'Test')
        # Confirm that the default settings have changed to the new settings
        actual = self.conn.channels[0].MotorDeviceSettings
        self.assertEqual(actual, 'Test')

    def test_start_polling_channels(self):
        """Test the start_polling_channels method."""
        method = 'microscope.controllers.bbd30x.' + \
            'BBD30XController.start_polling_single'
        with patch(method) as mocked_start_polling_single:
            self.conn.start_polling_channels('X')
            mocked_start_polling_single.assert_called()

    def test_start_polling_single(self):
        """Test the start_polling_single method."""
        method = 'microscope.controllers.bbd30x.' + \
            'SimulatedChannel.StartPolling'
        with patch(method) as mocked_start_polling:
            self.conn.start_polling_single('X')
            mocked_start_polling.assert_called()

    def test_enable_channels(self):
        """Test the enable_channels method."""
        method = 'microscope.controllers.bbd30x.' + \
            'BBD30XController.enable_single'
        with patch(method) as mocked_enable_single:
            self.conn.enable_channels('X')
            mocked_enable_single.assert_called()

    def test_enable_single(self):
        """Test the enable_single method."""
        # Confirm the default settings
        self.assertFalse(self.conn.channels[0].IsEnabled)
        # Set new settings
        self.conn.enable_single('X')
        # Confirm that the default settings have changed to the new settings
        self.assertTrue(self.conn.channels[0].IsEnabled)

    def test_disable_channels(self):
        """Test the disable_channels method."""
        method = 'microscope.controllers.bbd30x.' + \
            'BBD30XController.disable_single'
        with patch(method) as mocked_disable_single:
            self.conn.disable_channels('X')
            mocked_disable_single.assert_called()

    def test_disable_single(self):
        """Test the disable_single method."""
        self.conn.enable_single('X')
        # Confirm the pre-test settings
        self.assertTrue(self.conn.channels[0].IsEnabled)
        # Set new settings
        self.conn.disable_single('X')
        # Confirm that the pre-test settings have changed to the new settings
        self.assertFalse(self.conn.channels[0].IsEnabled)

    def test_make_channel_iterator(self):
        """Test the make_channel_iterator method."""
        iterator = self.conn._make_channel_iterator([1, 2, 3])
        self.assertEqual((1, 2, 3), iterator)

    def test_stop_polling_channels(self):
        """Test the stop_polling_channels method."""
        method = 'microscope.controllers.bbd30x.' + \
            'BBD30XController.stop_polling_single'
        with patch(method) as mocked_stop_polling_single:
            self.conn.stop_polling_channels('X')
            mocked_stop_polling_single.assert_called()

    def test_stop_polling_single(self):
        """Test the stop_polling_single method."""
        method = 'microscope.controllers.bbd30x.' + \
            'SimulatedChannel.StopPolling'
        with patch(method) as mocked_stop_polling:
            self.conn.stop_polling_single('X')
            mocked_stop_polling.assert_called()

    def test_home_channels(self):
        """Test the home_channels method."""
        method = 'microscope.controllers.bbd30x.' + \
            'BBD30XController.home_single'
        with patch(method) as mocked_home_single:
            self.conn.home_channels('X')
            mocked_home_single.assert_called()

    def test_home_single(self):
        """Test the home_single method."""
        self.assertFalse(self.conn.channels[0].Status.IsHomed)
        self.conn.home_single('X')
        self.assertTrue(self.conn.channels[0].Status.IsHomed)

    def test_move_to_fast(self):
        """Test the move_to_fast method."""
        method = 'microscope.controllers.bbd30x.' + \
            'SimulatedChannel.MoveTo'
        with patch(method) as mocked_move_to:
            self.conn.move_to_fast([20])
            mocked_move_to.assert_called()

    def test_move_to(self):
        """Test the move_to method."""
        method = 'microscope.controllers.bbd30x.' + \
            'BBD30XController.move_to_channel'
        with patch(method) as mocked_move_to_channel:
            self.conn.move_to([20], ['X'])
            mocked_move_to_channel.assert_called()

    def test_move_to_channel(self):
        """Test the move_to_channel method."""
        self.assertEqual(self.conn.channels[0].Position, 5)
        self.conn.move_to_channel(20, 'X')
        self.assertEqual(self.conn.channels[0].Position, 20)

    def test_move_to_channel_relative(self):
        """Test the move_to_channel_relative method."""
        method = 'microscope.controllers.bbd30x.' + \
            'BBD30XController.move_to_channel'
        with patch(method) as mocked_move_to_channel:
            self.conn.move_to_channel_relative(20, 'X')
            mocked_move_to_channel.assert_called()

    def test_set_velocity_params(self):
        """Test the set_velocity_params method."""
        method = 'microscope.controllers.bbd30x.' + \
            'BBD30XController.set_velocity_params_single'
        with patch(method) as mocked_set_velocity_params_single:
            self.conn.set_velocity_params('X')
            mocked_set_velocity_params_single.assert_called()

    def test_set_velocity_params_single(self):
        """Test the set_velocity_params_single method."""
        # Check the default settings
        self.assertEqual(self.conn.channels[0].MaxVelocity, 20)
        self.assertEqual(self.conn.channels[0].Acceleration, 10)
        # Change the settings
        self.conn.set_velocity_params_single('X', 200, 100)
        # Check that the settings have been changed
        self.assertEqual(self.conn.channels[0].MaxVelocity, 200)
        self.assertEqual(self.conn.channels[0].Acceleration, 100)

    @patch('sys.stdout', new_callable=StringIO)
    def test_print_position(self, mock_stdout):
        """Test the print_position method."""
        self.conn.print_position()
        expected = "Device position: channels ('X', 'Y') - [5.0, 5.0] mm"
        self.assertEqual(mock_stdout.getvalue().strip(), expected)

    def test_get_position_decimal(self):
        """Test the get_position_decimal method."""
        self.assertEqual(self.conn.get_position_decimal('X'), 5)

    def test_get_position_channel(self):
        """Test the get_position_channel method."""
        self.assertEqual(self.conn.get_position_channel('X'), 5)

    def test_get_velocity_params(self):
        """Test the get_velocity_params method."""
        max_vel, acc = self.conn.get_velocity_params('X')
        self.assertEqual(max_vel, 20)
        self.assertEqual(acc, 10)

    def test_get_position(self):
        """Test the get_position method."""
        position = self.conn.get_position()
        self.assertEqual(position, [5.0, 5.0])

    def test_disconnect(self):
        """Test the disconnect method."""
        method = 'microscope.controllers.bbd30x.' + \
            'SimulatedDevice.Disconnect'
        with patch(method) as mocked_disconnect:
            self.conn.disconnect()
            mocked_disconnect.assert_called()

    def test_finish(self):
        """Test the finish method."""
        method = 'microscope.controllers.bbd30x.' + \
            'BBD30XController.stop_polling_single'
        with patch(method) as mocked_stop_polling_single:
            method = 'microscope.controllers.bbd30x.' + \
                'SimulatedDevice.Disconnect'
            with patch(method) as mocked_disconnect:
                self.conn.finish('X')
                mocked_stop_polling_single.assert_called()
                mocked_disconnect.assert_called()

if __name__ == '__main__':
    unittest.main()
