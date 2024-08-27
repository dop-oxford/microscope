"""
Controller for the Thorlabs BBD30X Brushless Motor Controllers.

Author: Alvaro Fernandez Galiana (alvaro.fernandezgaliana@gmail.com)
Date: 2024-06-27

Notes:
    - Add units in description
    - Fix the channel, channel_name, channel_idx convention, particularly for
      the final methods, ensure that the channel number/name is given, and not
      the index or the channel object
    - Generally the approach should be that all methods called externally use
      the channel_name convention, and not the idx.
    - Check Decimal to Float conversion
"""
from collections.abc import Iterable
from decimal import Decimal
import time


class SimulatedVelocityParams:
    def __init__(
        self, acceleration, max_velocity, min_velocity
    ):
        self.Acceleration = acceleration
        self.MaxVelocity = max_velocity
        self.MinVelocity = min_velocity


class SimulatedChannel:
    def __init__(
        self, description, serial_no, device_type, hardware_version,
        firmware_version, acceleration=10, max_velocity=20, min_velocity=1
    ):
        self.Description = description
        self.SerialNumber = serial_no
        self.DeviceType = device_type
        self.HardwareVersion = hardware_version
        self.FirmwareVersion = firmware_version
        self.Acceleration = acceleration
        self.MaxVelocity = max_velocity
        self.MinVelocity = min_velocity
        self.MotorDeviceSettings = 'Simulated Motor Device Settings'
        self.IsEnabled = True
        self.Position = 0.0

    def GetDeviceInfo(self):
        return DeviceInfo(
            description=self.Description,
            serial_no=self.SerialNumber,
            device_type=self.DeviceType,
            hardware_version=self.HardwareVersion,
            firmware_version=self.FirmwareVersion
        )

    def GetVelocityParams(self):
        return SimulatedVelocityParams(
            acceleration=self.Acceleration,
            max_velocity=self.MaxVelocity,
            min_velocity=self.MinVelocity
        )

    def IsSettingsInitialized(self):
        return True

    def StartPolling(self, pol_rate):
        pass


class SimulatedDevice:
    def __init__(self):
        self.channels = [
            SimulatedChannel(
                description='Simulated Channel 1',
                serial_no='1',
                device_type='Simulated Channel',
                hardware_version='Simulated Hardware',
                firmware_version='Simulated Firmware'
            ),
            SimulatedChannel(
                description='Simulated Channel 2',
                serial_no='2',
                device_type='Simulated Channel',
                hardware_version='Simulated Hardware',
                firmware_version='Simulated Firmware'
            ),
        ]

    def GetChannel(self, num):
        # The channel 'num' is its index plus 1
        idx = num - 1
        return self.channels[idx]


class DeviceInfo:
    def __init__(
        self, description, serial_no, device_type, hardware_version,
        firmware_version
    ):
        self.Description = description
        self.SerialNumber = serial_no
        self.DeviceType = device_type
        self.HardwareVersion = hardware_version
        self.FirmwareVersion = firmware_version


class BBD30XController:

    def __init__(
        self, serial_no='103251384', name='BBD302', channel_names=('X', 'Y'),
        reverse=(False, False), simulated=False, verbose=True,
        very_verbose=False
    ):
        """
        Initialise the BBD30X controller.

        Parameters
        ----------
        serial_no : str, default '103251384'
            Serial number for Benchtop Brushless Motor.
        name : str, default 'BBD302'
            Name of the controller.
        channel_names : tuple of (str,), default ('X', 'Y')
            Channel names.
        reverse : tuple of (bool,), default (False, False)
            If channels are in reverse direction.
        simulated : bool, default False
            If the controller is being simulated in silico in lieu of real
            hardware being used.
        verbose : bool, default True
            If general information is printed to screen.
        very_verbose : bool, default False
            If detailed information is printed to screen.
        """
        self.serial_no = serial_no
        self.name = name
        self.verbose = verbose
        self.very_verbose = very_verbose
        self.simulated = simulated
        self.channel_names = channel_names
        self.reverse = reverse
        
        self.device_info = DeviceInfo(
            description=self.name,
            serial_no=self.serial_no,
            device_type='Controller',
            hardware_version='Unknown',
            firmware_version='Unknown'
        )

        # 1-indexed array of channel numbers
        self.channel_nums = range(1, len(self.channel_names) + 1)
        # Links name to channel number
        self.channel_nums_dict = \
            dict(zip(self.channel_names, self.channel_nums))
        # Tuple of the actual channels
        self.channels = (None,) * len(self.channel_names)
        # Create dictionary with channels names and channels
        self.channel_dict = dict(zip(self.channel_names, self.channels))

        # Check that there are enough objects in the `reverse` tuple
        assert len(self.reverse) >= len(self.channel_names), (
            f'More channels ({len(self.channel_names)}) than reverse '
            f'conditions ({len(self.reverse)})'
        )

        # Check that no name is duplicated
        assert len(self.channel_names) == len(set(self.channel_names)), (
            f'Duplicate channel names: {self.channel_names}'
        )

        if self.simulated:
            self.device = SimulatedDevice()
        else:
            # Build list of connected devices
            DeviceManagerCLI.BuildDeviceList()
            # Get all available devices
            self.device_list = DeviceManagerCLI.GetDeviceList()
            # Get available Benchtop Brushless Motors
            self.device_list_BBM = DeviceManagerCLI.GetDeviceList(
                BenchtopBrushlessMotor.DevicePrefix103
            )

            if self.very_verbose:
                print('------------------------')
                print('Device List:')
                print(self.device_list)
                print('Brushless Motor Device List:')
                print(self.device_list_BBM)
                print('------------------------')

            # Check/assign serial number
            if self.device_list_BBM:
                if self.serial_no:
                    if self.serial_no in self.device_list_BBM:
                        pass
                    else:
                        raise ValueError(
                            f'Serial number {self.serial_no} is not in the '
                            'list of devices available:'
                            f'{self.device_list_BBM}'
                        )
                else:
                    self.serial_no = self.device_list_BBM[0]
                    print(
                        f'The device serial number has been selected from the '
                        f'list and is {self.serial_no}'
                    )
            else:
                raise ValueError('There are no devices connected')

            # Create the device and check type
            try:
                if self.verbose:
                    print('Opening device...')
                self.device = \
                    BenchtopBrushlessMotor.CreateBenchtopBrushlessMotor(
                        self.serial_no
                    )
                self.device.Connect(self.serial_no)

                # Wait statements are important to allow settings to be sent
                # to the device
                time.sleep(0.25)

                if self.verbose:
                    print('------------------------')
                    print(f'Device class: {self.device}')
                    print('------------------------')

                # Get and print device info
                self.device_info = self.device.GetDeviceInfo()
                if self.verbose:
                    self.print_device_info()
            except Exception as e:
                print(
                    'Exception connecting to device serial number '
                    f'{self.serial_no}. Exception: {e}'
                )

            # Get motherboard configurations
            self.mb_config = self.device.GetMotherboardConfiguration(
                self.serial_no,
                DeviceConfiguration.DeviceSettingsUseOptionType.
                UseDeviceSettings
            )

            # Get synchronous controller
            # See https://github.com/Thorlabs/Motion_Control_Examples/blob/
            # main/C%23/Benchtop/BBD30X_Synch_Move/Program.cs
            self.synch_cont = self.device.GetSyncController()

        # Get channels
        self.get_channels(verbose=self.very_verbose)
        self.load_config_channels(verbose=self.very_verbose)
        self.set_setting_channels(verbose=self.very_verbose)

    def print_device_info(self):
        """Print the device information."""
        print('------------------------')
        print(f'DEVICE: {self.name}')
        print(f'Device Description: {self.device_info.Description}')
        print(f'Device Serial No: {self.device_info.SerialNumber}')
        print(f'Device Type: {self.device_info.DeviceType}')
        print(f'Device Hardware Version: {self.device_info.HardwareVersion}')
        print(f'Device Firmware Version: {self.device_info.FirmwareVersion}')
        print('------------------------')

    def print_channel_info(self, channel):
        """
        Print the channel information.

        Parameters
        ----------
        channel : str or int
            Channel name or number.
        """
        self._make_channel_iterator(channel)
        for chan in channel:
            chan_idx = self._get_channel_idx(chan)
            channel_info = self.channels[chan_idx].GetDeviceInfo()
            print('------------------------')
            print(f'Channel {chan} Info:')
            print(f'Class: {type(self.channels[chan_idx])}')
            print(f'Channel Description: {channel_info.Description}')
            print(f'Channel Serial No: {channel_info.SerialNumber}')
            print(f'Channel Type: {channel_info.DeviceType}')
            print(f'Channel Hardware Version: {channel_info.HardwareVersion}')
            print(f'Channel Firmware Version: {channel_info.FirmwareVersion}')
            print('------------------------')
        return None

    def print_velocity_params(self, channel=['X', 'Y']):
        """
        Print the velocity parameters of the channels.

        Parameters
        ----------
        channel : list, default ['X', 'Y']
            List of channel names or numbers.
        """
        self._make_channel_iterator(channel)
        for chan in channel:
            chan_idx = self._get_channel_idx(chan)
            vel_params = self.channels[chan_idx].GetVelocityParams()
            print('------------------------')
            print(f'Channel {chan} Velocity Parameters')
            print(f'Acceleration: {vel_params.Acceleration}')
            print(f'MaxVelocity: {vel_params.MaxVelocity}')
            print(f'MinVelocity: {vel_params.MinVelocity}')
            print('------------------------')
        return None

    def _decimal_to_float(self, decimal):
        """Convert Decimal to float.

        Args:
            decimal (Decimal): Decimal number.

        Returns:
            float: Float number.
        """
        # TODO: Write a test
        return float(str(decimal))

    def _get_channel_idx(self, channel):
        """
        Get the index of the channel.

        Parameters
        ----------
        channel : str or int
            Channel name or number.

        Returns
        -------
        int
            Index of the channel.
        """
        # TODO: Write a test
        if isinstance(channel, int):
            assert channel in self.channel_nums, (
                f'Channel number {channel} is not in the list of channels ' +
                f'for this device: {self.channel_nums}'
            )
            chan_idx = self.channel_nums.index(channel)
        elif isinstance(channel, str):
            assert channel in self.channel_names, (
                f'Channel name {channel} is not in the list of channels for ' +
                f'this device: {self.channel_names}'
            )
            chan_idx = self.channel_names.index(channel)
        else:
            raise Exception(
                'The channel is not integer or string, the type is ' +
                f'{type(channel)}.'
            )
        return chan_idx

    def get_channels(self, channel=None, verbose=False):
        """
        Get the specified channels.

        Parameters
        ----------
        channel : list or None, default None
            List of channel names or numbers. If None, gets all channels.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        if channel:
            for chan in self._make_channel_iterator(channel):
                self.get_channel_single(chan, verbose)
            if verbose:
                print(f'All channels {channel} were successfully gotten')
                print("------------------------")
        else:
            # If channel = None, get all the channels in the device
            self.get_channels(self.channel_names, verbose)
        return None

    def get_channel_single(self, channel=None, verbose=False):
        """
        Get a single channel.

        Parameters
        ----------
        channel : str, int or None, default None
            Channel name or number.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        chan_idx = self._get_channel_idx(channel)
        if isinstance(channel, int):
            chan_num = channel
        elif isinstance(channel, str):
            chan_num = self.channel_nums_dict[channel]
        else:
            raise Exception(
                f'The channel {channel} is not an integer or string, the type '
                f'is {type(channel)}.'
            )
        try:
            self.channels = list(self.channels)
            self.channels[chan_idx] = self.device.GetChannel(chan_num)
            self.channels = tuple(self.channels)
        except Exception as e:
            print(f'Exception connecting to channel {channel}. Exception: {e}')
        # Create dictionary with channels names and channels
        self.channel_dict = dict(zip(self.channel_names, self.channels))
        if verbose:
            print(f'Channel {channel} information:')
            self.print_channel_info(channel)
        # Ensure that the channel settings have been initialized
        if not self.channels[chan_idx].IsSettingsInitialized():
            # 10 second timeout
            self.channels[chan_idx].WaitForSettingsInitialized(10000)
            assert self.channels[chan_idx].IsSettingsInitialized() is True, (
                f'Channel {channel} has not been initialized'
            )
        if verbose:
            print(f'Channel {channel} was successfully gotten')
            print('------------------------')
        return None

    def load_config_channels(self, channel=None, verbose=False):
        """
        Load configuration settings for the specified channels.

        Parameters
        ----------
        channel : list or None, default None
            List of channel names or numbers. If None, loads settings for all
            channels.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        if channel:
            for chan in self._make_channel_iterator(channel):
                self.load_config_channel_single(chan, verbose)
            if verbose:
                print(f'Configuration loaded for all channels {channel}')
                print('------------------------')
        else:
            # If channel = None, load configs for all channels in the device
            self.load_config_channels(self.channel_names, verbose)
        return None

    def load_config_channel_single(self, channel=None, verbose=False):
        """
        Load configuration settings for a single channel.

        Parameters
        ----------
        channel : str or int, default None
            Channel name or number.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        chan_idx = self._get_channel_idx(channel)
        try:
            channel_config = self.channels[chan_idx].LoadMotorConfiguration(
                self.channels[chan_idx].DeviceID
            )
            if verbose:
                print(f'Channel {channel} configuration loaded:')
                print(channel_config)
        except Exception as e:
            print(
                'Exception raised loading configuration for channel ' +
                f'{channel}: {e}'
            )
        return None

    def set_setting_channels(
        self, channel=None, device_settings=None, verbose=False
    ):
        """
        Set settings for the specified channels.

        Parameters
        ----------
        channel : list or None, default None
            List of channel names or numbers. If None, sets settings for all
            channels.
        device_settings : list or None, default None
            List of device settings.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        if not channel:
            # If channel = None, do to all channels in the device
            self.set_setting_channels(
                self.channel_names, device_settings, verbose
            )
        else:
            channel = list(channel)
            # Check that no name/number is duplicate
            assert len(channel) == len(set(channel)), (
                f'Duplicate channel name/number: {channel}'
            )
            # Test if channels are given in numbers
            assert all(isinstance(n, int) for n in channel) or \
                all(isinstance(n, str) for n in channel), (
                    'The list of channels is not integers or strings.'
                )
            if isinstance(device_settings, (list, tuple)):
                assert len(device_settings) == len(channel), (
                    f'Mismatch between number of channels ({len(channel)}) '
                    f'and device_settings ({len(device_settings)})'
                )
            else:
                device_settings = len(channel) * [device_settings, ]
            for chan in channel:
                self.set_setting_channel_single(
                    chan, device_settings[channel.index(chan)], verbose
                )
            if verbose:
                print(f'Settings set for all channels: {channel}')
                print('------------------------')
        return None

    def set_setting_channel_single(
        self, channel=None, device_settings=None, verbose=False
    ):
        """
        Set settings for a single channel.

        Parameters
        ----------
        channel : str or int, default None
            Channel name or number.
        device_settings : unknown type, default None
            Device settings to apply.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        if not device_settings:
            this_channel = self.channels[self._get_channel_idx(channel)]
            device_settings = this_channel.MotorDeviceSettings
        try:
            this_channel = self.channels[self._get_channel_idx(channel)]
            this_channel.SetSettings(device_settings, False)
        except Exception as e:
            print(f'Exception raised setting channel {channel}: {e}')
        if verbose:
            print(f'Setting set for channel {channel}')
        return None

    def start_polling_channels(
        self, channel=None, pol_rate=250, verbose=False
    ):
        """
        Start polling specified channels.

        Parameters
        ----------
        channel : list or None, default None
            List of channel names or numbers. If None, starts polling for all
            channels.
        pol_rate : int, default 250
            Polling rate in milliseconds.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        if channel:
            for chan in self._make_channel_iterator(channel):
                self.start_polling_single(chan, pol_rate, verbose)
            if verbose:
                print(f'Polling all channels {channel}')
                print('------------------------')
        else:
            # If channel = None, start polling all channels in the device
            self.start_polling_channels(self.channel_names, pol_rate, verbose)
        return None

    def start_polling_single(self, channel=None, pol_rate=250, verbose=False):
        """
        Start polling a single channel.

        Parameters
        ----------
        channel : str, int or None, default None
            Channel name or number
        pol_rate : int, default 250
            Polling rate in milliseconds.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        # Polling rate in ms
        self.channels[self._get_channel_idx(channel)].StartPolling(pol_rate)
        if verbose:
            print(f'Polling channel {channel}')
        time.sleep(0.25)
        return None

    def enable_channels(self, channel=None, verbose=False):
        """
        Enable specified channels.

        Parameters
        ----------
        channel : list or None, default None
            List of channel names or numbers. If None, enables all channels.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        if channel:
            for chan in self._make_channel_iterator(channel):
                self.enable_single(chan, verbose)
            if verbose:
                print(f'All channels {channel} are ENABLED')
                print('------------------------')
        else:
            # If channel = None, do to all channels in the device
            self.enable_channels(self.channel_names, verbose)
        return None

    def enable_single(self, channel=None, verbose=False):
        """
        Enable a single channel.

        Parameters
        ----------
        channel : str, int or None, default None
            Channel name or number.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        chan_idx = self._get_channel_idx(channel)
        if not self.channels[chan_idx].IsEnabled:
            self.channels[self._get_channel_idx(channel)].EnableDevice()
            time.sleep(0.25)
            if verbose:
                print(f"Channel {channel} ENABLED")
        else:
            if verbose:
                print(f"Channel {channel} was already enabled")
        return None

    def disable_channels(self, channel=None, verbose=False):
        """
        Disable specified channels.

        Parameters
        ----------
        channel : list or None, default None
            List of channel names or numbers. If None, disables all channels.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        if channel:
            for chan in self._make_channel_iterator(channel):
                self.disable_single(chan, verbose)
            if verbose:
                print(f"All channels {channel} are DISABLED")
                print("------------------------")
        else:
            # If channel = None, disable all channels in the device
            self.disable_channels(self.channel_names, verbose)
        return None

    def disable_single(self, channel=None, verbose=False):
        """
        Disable a single channel.

        Parameters
        ----------
        channel : str or int, default None
            Channel name or number.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        chan_idx = self._get_channel_idx(channel)
        if self.channels[chan_idx].IsEnabled:
            self.channels[self._get_channel_idx(channel)].DisableDevice()
            time.sleep(0.25)
            if verbose:
                print(f'Channel {channel} DISABLED')
        else:
            if verbose:
                print(f'Channel {channel} was already disabled')
        return None

    def _make_channel_iterator(self, channel):
        """
        Make an iterator from the channel(s).

        Parameters
        ----------
        channel : list, tuple or str
            Single channel or list of channels.

        Returns
        -------
        tuple
            Tuple of channels over which to iterate.
        """
        # TODO: Write a test
        if not isinstance(channel, (list, tuple)):
            channel = (channel,)

        # Check that no names/numbers are duplicate
        assert len(channel) == len(set(channel)), (
            f'Duplicate channel name/number: {channel}'
        )
        # Test if channels are given in numbers or names
        assert all(isinstance(n, int) for n in channel) or \
            all(isinstance(n, str) for n in channel), (
                'The list of channels is not integers or strings.'
            )

        return tuple(channel)

    def stop_polling_channels(self, channel=None, verbose=False):
        """
        Stop polling specified channels.

        Parameters
        ----------
        channel : list or None, default None
            List of channel names or numbers. If None, stops polling for all
            channels.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        if channel:
            for chan in self._make_channel_iterator(channel):
                self.stop_polling_single(chan, verbose)
            if verbose:
                print(f"Stopped polling all channels {channel}")
                print("------------------------")
        else:
            # If channel = None, stop polling all channels in the device
            self.stop_polling_channels(self.channel_names, verbose)
        return None

    def stop_polling_single(self, channel=None, verbose=False):
        """
        Stop polling a single channel.

        Parameters
        ----------
        channel : str or int, default None
            Channel name or number.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        self.channels[self._get_channel_idx(channel)].StopPolling()
        if verbose:
            print(f'Stopped polling channel {channel}')
        time.sleep(0.25)
        return None

    def home_channels(self, channel=None, force=True, verbose=False):
        """
        Home specified channels.

        Parameters
        ----------
        channel : list or None, default None
            List of channel names or numbers. If None, homes all channels.
        force : bool, default True
            Whether to force homing even if already homed.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        if channel:
            for chan in self._make_channel_iterator(channel):
                self.home_single(chan, force, verbose)
            if verbose:
                print(f'All channels {channel} are HOMED')
                print('------------------------')
        else:
            # If channel = None, home all channels in the device
            self.home_channels(self.channel_names, force, verbose)
        return None

    def home_single(self, channel=None, force=True, verbose=False):
        """
        Home a single channel.

        Parameters
        ----------
        channel : str or int, default None
            Channel name or number.
        force : bool, default True
            Whether to force homing even if already homed.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        chan_idx = self._get_channel_idx(channel)
        assert self.channels[chan_idx].NeedsHoming, (
            f'Channel {self.channels[chan_idx]} does not need homing'
        )
        if not self.channels[chan_idx].Status.IsHomed or force:
            assert self.channels[chan_idx].CanHome, (
                f'Channel {self.channels[chan_idx]} cannot home'
            )
            if verbose:
                print(f'Homing Channel {channel}...')
            # 60 second timeout
            self.channels[chan_idx].Home(60000)
            time.sleep(0.25)
            assert self.channels[chan_idx].Status.IsHomed, (
                f'Channel {self.channels[chan_idx]} was not HOMED after 60 ' +
                'seconds'
            )
            if verbose:
                print(f'Channel {channel} HOMED')
        else:
            print(f'Channel {channel} was already homed')
        return None

    def moveToFast(self, target_pos):
        """
        Move channels to specified positions quickly.

        Parameters
        ----------
        target_pos : list
            List of end positions for each channel.
        """
        # TODO: Write a test
        for chan_idx, chan_target_pos in enumerate(target_pos):
            try:
                # 60 second timeout
                self.channels[chan_idx].MoveTo(
                    Decimal(float(chan_target_pos)), 60000
                )
            except Exception as e:
                print(
                    f'Exception raised moving channel {chan_idx} ' +
                    f'{self.channels[chan_idx]} to {chan_target_pos} mm: {e}'
                )

    def moveTo(
        self, target_pos, channel=None, relative=False, max_vel=None, acc=None,
        permanent=False, verbose=False
    ):
        """
        Move channels to specified positions.

        Parameters
        ----------
        target_pos : list
            List of end positions for each channel.
        channel : list or None, default None
            List of channel names or numbers. If None, moves all channels.
        relative : bool, default False
            If True, the movement is relative to the current position.
        max_vel : float or None, default None.
            Maximum velocity.
        acc : float or None, default None
            Acceleration.
        permanent : bool, default False
            Whether to make velocity and acceleration changes permanent.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        if not channel:
            channel = self.channel_names
        channel = self._make_channel_iterator(channel)
        if type(target_pos) is not Iterable:
            target_pos = [target_pos]
        if len(target_pos) != len(channel):
            raise ValueError(
                f'Number of target positions ({len(target_pos)}) does not ' +
                f'match the number of channels ({len(channel)})'
            )
        for chan_idx in range(len(channel)):
            # max_vel and acc are set to none since they have already been
            # changed
            self.moveTo_channel(
                target_pos[chan_idx], channel[chan_idx], relative, max_vel,
                acc, permanent, verbose
            )
        if verbose:
            self.print_position()
        return None

    def moveTo_channel(
        self, target_pos, channel, relative=False, max_vel=None, acc=None,
        permanent=False, verbose=False
    ):
        """
        Move a single channel to the specified position.

        Parameters
        ----------
        target_pos : float
            End position.
        channel : str or int
            Channel name or number.
        relative : bool, default False
            If True, the movement is relative to the current position.
        max_vel : float or None, default None
            Maximum velocity.
        acc : float or None, default None
            Acceleration.
        permanent : bool, default False
            Whether to make velocity and acceleration changes permanent.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        chan_idx = self._get_channel_idx(channel)
        vel_params_original = None
        if verbose:
            print(f'Moving channel {channel} to {str(target_pos)} mm...')
        if relative:
            target_pos = self.get_position_channel(channel) + target_pos
        # TODO: Fix this and make it coherent
        target_pos = Decimal(float(target_pos))
        if max_vel or acc:  # If either maxVel or acc are given
            vel_params_original = self.get_velocity_params(channel, verbose)
            self.set_velocity_params(channel, max_vel, acc, verbose)
        try:
            # 60 second timeout
            self.channels[chan_idx].MoveTo(target_pos, 60000)
        except Exception as e:
            print(
                f'Exception raised moving channel {channel} to ' +
                f'{str(target_pos)} mm: {e}'
            )
        time.sleep(0.25)
        if verbose:
            time.sleep(0.25)
            print(
                f'Channel {channel} in position ' +
                f'{self.get_position_channel(channel)}'
            )
        if vel_params_original and not permanent:
            # If it has been changed (ie it is not None any more)
            # self.channels[chan_idx].SetVelocityParams(*vel_params_original)
            self.set_velocity_params(
                channel=channel, max_vel=vel_params_original[0],
                acc=vel_params_original[1], verbose=verbose
            )
        return None

    def moveTo_channel_relative(
        self, rel_pos, channel, max_vel=None, acc=None, permanent=False,
        verbose=False
    ):
        """
        Move a single channel to the specified position.

        Parameters
        ----------
        rel_pos : float
            Relative position.
        channel : str or int
            Channel name or number.
        max_vel : float or None, default None
            Maximum velocity.
        acc : float or None, default None
            Acceleration.
        permanent : bool, default False
            Whether to make velocity and acceleration changes permanent.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        self.moveTo_channel(
            target_pos=rel_pos, channel=channel, relative=True,
            max_vel=max_vel, acc=acc, permanent=permanent, verbose=verbose
        )

    def set_velocity_params(
        self, channel=None, max_vel=None, acc=None, verbose=False
    ):
        """
        Set velocity parameters for the specified channels.

        Parameters
        ----------
        channel : list or None, default None
            List of channel names or numbers. If None, sets parameters for all
            channels.
        max_vel : float or None, default None
            Maximum velocity.
        acc : float or None, default None
            Acceleration.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        if channel:
            channel = self._make_channel_iterator(channel)
            max_vel = (max_vel,) if max_vel is not None else None
            acc = (acc,) if acc is not None else None
            if max_vel is not None:
                if len(max_vel) == 1:
                    max_vel = len(channel) * (max_vel[0],)
                else:
                    assert len(max_vel) == len(channel), (
                        f'The number of max_vel ({len(max_vel)}) does not ',
                        f'match the number of channels ({len(channel)})'
                    )
            if acc is not None:
                if len(acc) == 1:
                    acc = len(channel) * (acc[0],)
                else:
                    assert len(acc) == len(channel), (
                        f'The number of acc ({len(acc)}) does not match the '
                        f'number of channels ({len(channel)})'
                    )
            for chan_idx in range(len(channel)):
                self.set_velocity_params_single(
                    channel[chan_idx],
                    max_vel[chan_idx] if max_vel else None,
                    acc[chan_idx] if acc else None,
                    verbose
                )
            if verbose:
                print(f'Velocity params for all channels {channel} set at:')
                print(f'Max vel: {max_vel} mm/s')
                print(f'Acceleration: {acc} mm/s2')
                print('------------------------')
        else:
            # If channel = None, set parameters for all channels in the device
            self.set_velocity_params(self.channel_names, max_vel, acc, verbose)
        return None

    def set_velocity_params_single(
        self, channel=None, max_vel=None, acc=None, verbose=False
    ):
        """
        Set velocity parameters for a single channel.

        Parameters
        ----------
        channel : str or int, default None
            Channel name or number.
        max_vel : float or None, default None
            Maximum velocity.
        acc : float or None, default None
            Acceleration.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        chan_idx = self._get_channel_idx(channel)

        if max_vel is not None:
            if isinstance(max_vel, (int, float)):
                max_vel = Decimal(max_vel)
        else:
            # If no max vel is given, take the one that is already set
            max_vel = self.channels[chan_idx].GetVelocityParams().MaxVelocity

        if acc is not None:
            if isinstance(acc, (int, float)):
                acc = Decimal(acc)
        else:
            # If no acceleration is given, take the one that is already set
            acc = self.channels[chan_idx].GetVelocityParams().Acceleration

        try:
            self.channels[chan_idx].SetVelocityParams(max_vel, acc)
        except Exception as e:
            print(
                f'Exception setting velocity params for channel {channel}: {e}'
            )

        if verbose:
            max_vel = self.channels[chan_idx].GetVelocityParams().MaxVelocity
            acc = self.channels[chan_idx].GetVelocityParams().Acceleration
            print(f'Velocity parameters for channel {channel} set at:')
            print(f'Max vel {str(max_vel)} mm/s')
            print(f'Acceleration: {str(acc)} mm/s²')
        return None

    def print_position(self):
        """Print the current position of the device."""
        # TODO: Write a test
        name = self.channel_names
        position = self.get_position()
        print(f'Device position: channels {name} - {position} mm')

    def get_position_decimal(self, channel):
        """
        Get the current position of a single channel in Decimal.

        Parameters
        ----------
        channel : str or int
            Channel name or number.

        Returns
        -------
        Decimal
            Current position of the channel.
        """
        # TODO: Write a test
        return self.channels[self._get_channel_idx(channel)].Position

    def get_position_channel(self, channel, verbose=False):
        """
        Get the current position of a single channel.

        Parameters
        ----------
        channel : str or int
            Channel name or number.
        verbose : bool, default False
            Whether to print additional information.

        Returns
        -------
        float
            Current position of the channel.
        """
        # TODO: Write a test
        pos = self._decimal_to_float(self.get_position_decimal(channel))
        if verbose:
            print(f'Channel {channel} is in position {pos} mm')
        return pos

    def get_velocity_params(self, channel, verbose=False):
        """
        Get the velocity parameters of a single channel.

        Parameters
        ----------
        channel : str or int
            Channel name or number.
        verbose : bool, default False
            Whether to print additional information.

        Returns
        -------
        tuple
            Tuple of acceleration and maximum velocity.
        """
        # TODO: Write a test
        this_channel = self.channels[self._get_channel_idx(channel)]
        velParams = this_channel.GetVelocityParams()
        if verbose:
            print(f'Channel {channel} velocity parameters are:')
            print(f'Acceleration: {velParams.Acceleration} mm/s²')
            print(f'MaxVelocity: {velParams.MaxVelocity} mm/s')
        max_vel = self._decimal_to_float(velParams.MaxVelocity)
        acc = self._decimal_to_float(velParams.Acceleration)
        return max_vel, acc

    def get_position(self, verbose=False):
        """
        Get the current position of the device.

        Parameters
        ----------
        verbose : bool, default False
            Whether to print additional information.

        Returns
        -------
        list
            List of current positions for each channel.
        """
        # TODO: Write a test
        pos = [
            self.get_position_channel(chan, verbose=verbose)
            for chan in self.channel_names
        ]
        return pos

    def disconnect(self, verbose=False):
        """
        Disconnect the device.

        Parameters
        ----------
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        self.device.Disconnect()
        if verbose:
            print(f'Device {self.name} is DISCONNECTED')
        return None

    def finish(self, verbose=False):
        """
        Stop polling and disconnect the device.

        Parameters
        ----------
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        self.stop_polling_channels(verbose=verbose)
        self.disconnect(verbose=verbose)

    def standard_initialize_channels(
        self, home=True, force_home=False, verbose=False
    ):
        """Standard initialization of the channels.

        Parameters
        ----------
        home : bool, default True
            Whether to home the channels.
        force_home : bool, default False
            Whether to force homing even if already homed.
        verbose : bool, default False
            Whether to print additional information.
        """
        # TODO: Write a test
        self.start_polling_channels(verbose=verbose)
        self.enable_channels(verbose=verbose)
        if home:
            self.home_channels(force=force_home, verbose=verbose)

    def channel_IsEnabled(self, channel):
        """Determine whether this channel device is enabled.

        Args:
            channel (any): Channel object.

        Returns:
            bool: True if the channel is enabled, False otherwise.
        """
        # TODO: Write a test
        return channel.IsEnabled

    def channel_IsHomed(self, channel):
        """Determine whether this motor is homed.

        Args:
            channel (any): Channel object.

        Returns:
            bool: True if the channel is homed, False otherwise.
        """
        # TODO: Write a test
        return channel.Status.IsHomed

    def channel_IsHoming(self, channel):
        """Determine whether this motor is homing.

        Args:
            channel (any): Channel object.

        Returns:
            bool: True if the channel is homing, False otherwise.
        """
        # TODO: Write a test
        return channel.Status.IsHoming

    def channel_IsInMotion(self, channel):
        """Determine whether this motor is in motion.

        Args:
            channel (any): Channel object.

        Returns:
            bool: True if the channel is in motion, False otherwise.
        """
        # TODO: Write a test
        return channel.Status.IsInMotion

    def channel_Position(self, channel):
        """Get the position in Real World Units.

        Args:
            channel (any): Channel object.

        Returns:
            Decimal: Current position in Real World Units.
        """
        # TODO: Write a test
        return channel.Position

    def channel_Velocity(self, channel):
        """Get the current velocity.

        Args:
            channel (any): Channel object.

        Returns:
            float: Current velocity.
        """
        # TODO: Write a test
        return channel.Status.Velocity

    def channel_IsSettled(self, channel):
        """Determine whether the device is in a settled state.

        Args:
            channel (any): Channel object.

        Returns:
            bool: True if the channel is settled, False otherwise.
        """
        # TODO: Write a test
        return channel.Status.IsSettled

    def test_basic(self):
        """Test basic functionality of the device."""
        # TODO: Write a test
        self.standard_initialize_channels(home=False, verbose=True)
        self.print_position()
        self.print_velocity_params()
        # self.set_velocity_params(max_vel=200, acc=1100, verbose=True)
        # self.print_velocity_params()
        # self.print_position()
        # self.finish(verbose=True)


if __name__ == '__main__':
    # Initialise a simulated test controller
    name = 'BBD30X'
    conn = BBD30XController(
        name=name, simulated=True, verbose=True, very_verbose=True
    )

    conn.test_basic()
    # conn.moveTo([53.452546, 30.3564564], max_vel=10, acc=200, verbose=True)
    # conn.finish(verbose=True)
