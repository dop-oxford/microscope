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
import time


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

        if not self.simulated:
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
                    self.serialNo
                )
                self.device.Connect(self.serialNo)

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

            # # Get motherboard configurations
            # self.mb_config = self.device.GetMotherboardConfiguration(
            #     self.serial_no,
            #     DeviceConfiguration.DeviceSettingsUseOptionType.
            #     UseDeviceSettings
            # )

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
        print("------------------------")
        print(f"DEVICE: {self.name}")
        print(f"Device Description: {self.device_info.Description}")
        print(f"Device Serial No: {self.device_info.SerialNumber}")
        print(f"Device Type: {self.device_info.DeviceType}")
        print(f"Device Hardware Version: {self.device_info.HardwareVersion}")
        print(f"Device Firmware Version: {self.device_info.FirmwareVersion}")
        print("------------------------")


    def print_channel_info(self, channel):
        """Print the channel information.

        Args:
            channel (str or int): Channel name or number.
        """
        self._make_channel_iterator(channel)
        for chan in channel:
            chan_idx = self._get_channel_idx(chan)
            channel_info = self.channels[chan_idx].GetDeviceInfo()
            print(f"Channel {chan} Info:")
            print(f"Class: {self.channels[chan_idx]}")
            print(f"Channel Description: {channel_info.Description}")
            print(f"Channel Serial No: {channel_info.SerialNumber}")
            print(f"Channel Type: {channel_info.DeviceType}")
            print(f"Channel Hardware Version: {channel_info.HardwareVersion}")
            print(f"Channel Firmware Version: {channel_info.FirmwareVersion}")
            print("------------------------")
        return None

    def print_velocity_params(self, channel=['X', 'Y']):
        """Print the velocity parameters of the channels.

        Args:
            channel (list, optional): List of channel names or numbers. Defaults to ['X', 'Y'].
        """
        self._make_channel_iterator(channel)
        for chan in channel:
            chan_idx = self._get_channel_idx(chan)
            velParams = self.channels[chan_idx].GetVelocityParams()
            print(f"Channel {chan} Velocity Parameters")
            print(f"Acceleration: {velParams.Acceleration}")
            print(f"MaxVelocity: {velParams.MaxVelocity}")
            print(f"MinVelocity: {velParams.MinVelocity}")
            print("------------------------")
        return None


    def _decimal_to_float(self, decimal):
        """Convert Decimal to float.

        Args:
            decimal (Decimal): Decimal number.

        Returns:
            float: Float number.
        """
        return float(str(decimal))        


    def _get_channel_idx(self, channel):
        """Get the index of the channel.

        Args:
            channel (str or int): Channel name or number.

        Returns:
            int: Index of the channel.
        """
        if isinstance(channel, int):
            assert channel in self.channel_nums, f"Channel number {channel} is not in the list of channels for this device: {self.channel_nums}"
            chan_idx = self.channel_nums.index(channel)
        elif isinstance(channel, str):
            assert channel in self.channel_names, f"Channel name {channel} is not in the list of channels for this device: {self.channel_names}"
            chan_idx = self.channel_names.index(channel)
        else:
            raise Exception(f"The channel is not integer or string, the type is {type(channel)}.")
        return chan_idx

    def get_channels(self, channel=None, verbose=False):
        """Get the specified channels.

        Args:
            channel (list or None, optional): List of channel names or numbers. If None, gets all channels. Defaults to None.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        if channel:
            for chan in self._make_channel_iterator(channel):
                self.get_channel_single(chan, verbose)
            if verbose:
                print(f"All channels {channel} were successfully gotten")
                print("------------------------")
        else:
            self.get_channels(self.channel_names, verbose)  # If channel = None, do to all channels in the device
        return None

    def get_channel_single(self, channel=None, verbose=False):
        """Get a single channel.

        Args:
            channel (str or int, optional): Channel name or number. Defaults to None.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        chan_idx = self._get_channel_idx(channel)
        if isinstance(channel, int):
            chan_num = channel
        elif isinstance(channel, str):
            chan_num = self.channel_nums_dict[channel]
        else:
            raise Exception(f"The channel {channel} is not integer or string, the type is {type(channel)}.")
        try:
            self.channels = list(self.channels)
            self.channels[chan_idx] = self.device.GetChannel(chan_num)
            self.channels = tuple(self.channels)
        except Exception as e:
            print(f'Exception connecting to channel {channel}. Exception: {e}')
        self.channel_dict = dict(zip(self.channel_names, self.channels))  # Create dictionary with channels names and channels
        if verbose:
            print(f"Channel {channel} information:")
            self.print_channel_info(channel)
        # Ensure that the channel settings have been initialized
        if not self.channels[chan_idx].IsSettingsInitialized():
            self.channels[chan_idx].WaitForSettingsInitialized(10000)  # 10 second timeout
            assert self.channels[chan_idx].IsSettingsInitialized() is True, print(f"Channel {channel} has not been initialized")
        if verbose:
            print(f"Channel {channel} was successfully gotten")
            print("------------------------")
        return None

    def load_config_channels(self, channel=None, verbose=False):
        """Load configuration settings for the specified channels.

        Args:
            channel (list or None, optional): List of channel names or numbers. If None, loads settings for all channels. Defaults to None.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        if channel:
            for chan in self._make_channel_iterator(channel):
                self.load_config_channel_single(chan, verbose)
            if verbose:
                print(f"Configuration loaded for all channels {channel}")
                print("------------------------")
        else:
            self.load_config_channels(self.channel_names, verbose)  # If channel = None, do to all channels in the device
        return None

    def load_config_channel_single(self, channel=None, verbose=False):
        """Load configuration settings for a single channel.

        Args:
            channel (str or int, optional): Channel name or number. Defaults to None.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        chan_idx = self._get_channel_idx(channel)
        try:
            channel_config = self.channels[chan_idx].LoadMotorConfiguration(self.channels[chan_idx].DeviceID)
        except Exception as e:
            print(f'Exception raised loading configuration for channel {channel}: {e}')
        if verbose:
            print(f"Channel {channel} configuration loaded:")
            print(channel_config)
        return None

    def set_setting_channels(self, channel=None, deviceSettings=None, verbose=False):
        """Set settings for the specified channels.

        Args:
            channel (list or None, optional): List of channel names or numbers. If None, sets settings for all channels. Defaults to None.
            deviceSettings (list or None, optional): List of device settings. Defaults to None.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        if not channel:
            self.set_setting_channels(self.channel_names, deviceSettings, verbose)  # If channel = None, do to all channels in the device
        else:
            channel = list(channel)
            assert len(channel) == len(set(channel)), f"Duplicate channel name/number: {channel}"  # Check that no name/number is duplicate
            assert all(isinstance(n, int) for n in channel) or all(isinstance(n, str) for n in channel), "The list of channels is not integers or strings."  # Test if channels are given in numbers
            if isinstance(deviceSettings, (list, tuple)):
                assert len(deviceSettings) == len(channel), f"Mismatch between number of channels ({len(channel)}) and deviceSettings ({len(deviceSettings)})"
            else:
                deviceSettings = len(channel) * [deviceSettings, ]
            for chan in channel:
                self.set_setting_channel_single(chan, deviceSettings[channel.index(chan)], verbose)
            if verbose:
                print(f"Settings set for all channels: {channel}")
                print("------------------------")
        return None

    def set_setting_channel_single(self, channel=None, deviceSettings=None, verbose=False):
        """Set settings for a single channel.

        Args:
            channel (str or int, optional): Channel name or number. Defaults to None.
            deviceSettings (any, optional): Device settings to apply. Defaults to None.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        if not deviceSettings:
            deviceSettings = self.channels[self._get_channel_idx(channel)].MotorDeviceSettings
        try:
            self.channels[self._get_channel_idx(channel)].SetSettings(deviceSettings, False)
        except Exception as e:
            print(f'Exception raised setting channel {channel}: {e}')
        if verbose:
            print(f"Setting set for channel {channel}")
        return None

    def start_polling_channels(self, channel=None, pol_rate=250, verbose=False):
        """Start polling specified channels.

        Args:
            channel (list or None, optional): List of channel names or numbers. If None, starts polling for all channels. Defaults to None.
            pol_rate (int, optional): Polling rate in milliseconds. Defaults to 250.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        if channel:
            for chan in self._make_channel_iterator(channel):
                self.start_polling_single(chan, pol_rate, verbose)
            if verbose:
                print(f"Polling all channels {channel}")
                print("------------------------")
        else:
            self.start_polling_channels(self.channel_names, pol_rate, verbose)  # If channel = None, do to all channels in the device
        return None

    def start_polling_single(self, channel=None, pol_rate=250, verbose=False):
        """Start polling a single channel.

        Args:
            channel (str or int, optional): Channel name or number. Defaults to None.
            pol_rate (int, optional): Polling rate in milliseconds. Defaults to 250.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        self.channels[self._get_channel_idx(channel)].StartPolling(pol_rate)  # polling rate in ms
        if verbose:
            print(f"Polling channel {channel}")
        time.sleep(0.25)
        return None

    def enable_channels(self, channel=None, verbose=False):
        """Enable specified channels.

        Args:
            channel (list or None, optional): List of channel names or numbers. If None, enables all channels. Defaults to None.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        if channel:
            for chan in self._make_channel_iterator(channel):
                self.enable_single(chan, verbose)
            if verbose:
                print(f"All channels {channel} are ENABLED")
                print("------------------------")
        else:
            self.enable_channels(self.channel_names, verbose)  # If channel = None, do to all channels in the device
        return None

    def enable_single(self, channel=None, verbose=False):
        """Enable a single channel.

        Args:
            channel (str or int, optional): Channel name or number. Defaults to None.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
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
        """Disable specified channels.

        Args:
            channel (list or None, optional): List of channel names or numbers. If None, disables all channels. Defaults to None.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        if channel:
            for chan in self._make_channel_iterator(channel):
                self.disable_single(chan, verbose)
            if verbose:
                print(f"All channels {channel} are DISABLED")
                print("------------------------")
        else:
            self.disable_channels(self.channel_names, verbose)  # If channel = None, do to all channels in the device
        return None

    def disable_single(self, channel=None, verbose=False):
        """Disable a single channel.

        Args:
            channel (str or int, optional): Channel name or number. Defaults to None.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        chan_idx = self._get_channel_idx(channel)
        if self.channels[chan_idx].IsEnabled:
            self.channels[self._get_channel_idx(channel)].DisableDevice()
            time.sleep(0.25)
            if verbose:
                print(f"Channel {channel} DISABLED")
        else:
            if verbose:
                print(f"Channel {channel} was already disabled")
        return None

    def _make_channel_iterator(self, channel):
        """Make an iterator from the channel(s).

        Args:
            channel (any): Single channel or list of channels.

        Returns:
            tuple: Tuple of channels to iterate over.
        """
        if not isinstance(channel, (list, tuple)):
            channel = (channel,)
        
        assert len(channel) == len(set(channel)), f"Duplicate channel name/number: {channel}"  # Check that no name/number is duplicate
        assert all(isinstance(n, int) for n in channel) or all(isinstance(n, str) for n in channel), "The list of channels is not integers or strings."  # Test if channels are given in numbers or names
        
        return tuple(channel)


    def stop_polling_channels(self, channel=None, verbose=False):
        """Stop polling specified channels.

        Args:
            channel (list or None, optional): List of channel names or numbers. If None, stops polling for all channels. Defaults to None.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        if channel:
            for chan in self._make_channel_iterator(channel):
                self.stop_polling_single(chan, verbose)
            if verbose:
                print(f"Stopped polling all channels {channel}")
                print("------------------------")
        else:
            self.stop_polling_channels(self.channel_names, verbose)  # If channel = None, do to all channels in the device
        return None

    def stop_polling_single(self, channel=None, verbose=False):
        """Stop polling a single channel.

        Args:
            channel (str or int, optional): Channel name or number. Defaults to None.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        self.channels[self._get_channel_idx(channel)].StopPolling()
        if verbose:
            print(f"Stopped polling channel {channel}")
        time.sleep(0.25)
        return None

    def home_channels(self, channel=None, force=True, verbose=False):
        """Home specified channels.

        Args:
            channel (list or None, optional): List of channel names or numbers. If None, homes all channels. Defaults to None.
            force (bool, optional): Whether to force homing even if already homed. Defaults to True.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        if channel:
            for chan in self._make_channel_iterator(channel):
                self.home_single(chan, force, verbose)
            if verbose:
                print(f"All channels {channel} are HOMED")
                print("------------------------")
        else:
            self.home_channels(self.channel_names, force, verbose)  # If channel = None, do to all channels in the device
        return None

    def home_single(self, channel=None, force=True, verbose=False):
        """Home a single channel.

        Args:
            channel (str or int, optional): Channel name or number. Defaults to None.
            force (bool, optional): Whether to force homing even if already homed. Defaults to True.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        chan_idx = self._get_channel_idx(channel)
        assert self.channels[chan_idx].NeedsHoming, f"Channel {self.channels[chan_idx]} does not need homing"
        if not self.channels[chan_idx].Status.IsHomed or force:
            assert self.channels[chan_idx].CanHome, f"Channel {self.channels[chan_idx]} cannot home"
            if verbose:
                print(f"Homing Channel {channel}...")
            self.channels[chan_idx].Home(60000)  # 60 second timeout
            time.sleep(0.25)
            assert self.channels[chan_idx].Status.IsHomed, f"Channel {self.channels[chan_idx]} was not HOMED after 60 seconds"
            if verbose:
                print(f"Channel {channel} HOMED")
        else:
            print(f"Channel {channel} was already homed")
        return None

    def moveToFast(self, target_pos):
        """Move channels to specified positions quickly.

        Args:
            target_pos (list): List of end positions for each channel.
        """
        for chan_idx, chan_target_pos in enumerate(target_pos):
            try:
                self.channels[chan_idx].MoveTo(Decimal(float(chan_target_pos)), 60000)  # 60 second timeout
            except Exception as e:
                print(f'Exception raised moving channel {chan_idx} {self.channels[chan_idx]} to {chan_target_pos} mm: {e}')

    def moveTo(self, target_pos, channel=None, relative=False, max_vel=None, acc=None, permanent=False, verbose=False):
        """Move channels to specified positions.

        Args:
            target_pos (list): List of end positions for each channel.
            channel (list or None, optional): List of channel names or numbers. If None, moves all channels. Defaults to None.
            relative (bool): If True, the movement is relative to the current position.
            max_vel (float or None, optional): Maximum velocity. Defaults to None.
            acc (float or None, optional): Acceleration. Defaults to None.
            permanent (bool, optional): Whether to make velocity and acceleration changes permanent. Defaults to False.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        if not channel:
            channel = self.channel_names
        channel = self._make_channel_iterator(channel)
        if type(target_pos) is not Iterable:
            target_pos = [target_pos]
        if len(target_pos) != len(channel):
            raise ValueError(f"Number of target positions ({len(target_pos)}) does not match the number of channels ({len(channel)})")
        for chan_idx in range(len(channel)):
            self.moveTo_channel(target_pos[chan_idx], channel[chan_idx], relative, max_vel, acc, permanent, verbose)  # max_vel and acc are set to none since they have already been changed
        if verbose:
            self.print_position()
        return None

    def moveTo_channel(self, target_pos, channel, relative=False, max_vel=None, acc=None, permanent=False, verbose=False):
        """Move a single channel to the specified position.

        Args:
            target_pos (float): End position.
            channel (str or int): Channel name or number.
            relative (bool): If True, the movement is relative to the current position.
            max_vel (float or None, optional): Maximum velocity. Defaults to None.
            acc (float or None, optional): Acceleration. Defaults to None.
            permanent (bool, optional): Whether to make velocity and acceleration changes permanent. Defaults to False.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        chan_idx = self._get_channel_idx(channel)
        vel_params_original = None
        if verbose:
            print(f'Moving channel {channel} to {str(target_pos)} mm...')
        if relative: target_pos = self.get_position_channel(channel) + target_pos
        target_pos = Decimal(float(target_pos))  # TODO -> fix this and make it coherent
        if max_vel or acc:  # If either maxVel or acc are given
            vel_params_original = self.get_velocity_params(channel, verbose)
            self.set_velocity_params(channel, max_vel, acc, verbose)
        try:
            self.channels[chan_idx].MoveTo(target_pos, 60000)  # 60 second timeout
        except Exception as e:
            print(f'Exception raised moving channel {channel} to {str(target_pos)} mm: {e}')
        time.sleep(0.25)
        if verbose:
            time.sleep(0.25)
            print(f"Channel {channel} in position {self.get_position_channel(channel)}")
        if vel_params_original and not permanent:  # if it has been changed (i.e. it is not None anymore)
            #self.channels[chan_idx].SetVelocityParams(*vel_params_original)
            self.set_velocity_params(channel=channel, max_vel=vel_params_original[0], acc=vel_params_original[1], verbose=verbose)
        return None

    def moveTo_channel_relative(self, rel_pos, channel, max_vel=None, acc=None, permanent=False, verbose=False):
        """Move a single channel to the specified position.

        Args:
            rel_pos (float): Relative position.
            channel (str or int): Channel name or number.
            max_vel (float or None, optional): Maximum velocity. Defaults to None.
            acc (float or None, optional): Acceleration. Defaults to None.
            permanent (bool, optional): Whether to make velocity and acceleration changes permanent. Defaults to False.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        self.moveTo_channel(target_pos=rel_pos, channel=channel, relative=True, max_vel=max_vel, acc=acc, permanent=permanent, verbose=verbose)
        
        
    def set_velocity_params(self, channel=None, max_vel=None, acc=None, verbose=False):
        """Set velocity parameters for the specified channels.

        Args:
            channel (list or None, optional): List of channel names or numbers. If None, sets parameters for all channels. Defaults to None.
            max_vel (float or None, optional): Maximum velocity. Defaults to None.
            acc (float or None, optional): Acceleration. Defaults to None.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        if channel:
            channel = self._make_channel_iterator(channel)
            max_vel = (max_vel,) if max_vel is not None else None
            acc = (acc,) if acc is not None else None
            if max_vel is not None:
                if len(max_vel) == 1:
                    max_vel = len(channel) * (max_vel[0],)
                else:
                    assert len(max_vel) == len(channel), f"The number of max_vel ({len(max_vel)}) does not match the number of channels ({len(channel)})"
            if acc is not None:
                if len(acc) == 1:
                    acc = len(channel) * (acc[0],)
                else:
                    assert len(acc) == len(channel), f"The number of acc ({len(acc)}) does not match the number of channels ({len(channel)})"
            for chan_idx in range(len(channel)):
                self.set_velocity_params_single(channel[chan_idx], max_vel[chan_idx] if max_vel else None, acc[chan_idx] if acc else None, verbose)
            if verbose:
                print(f'Velocity parameters for all channels {channel} set at:\n', f'Max vel {max_vel} mm/s\n', f'Acceleration: {acc} mm/s2')
                print("------------------------")
        else:
            self.set_velocity_params(self.channel_names, max_vel, acc, verbose)  # If channel = None, do to all channels in the device
        return None

    def set_velocity_params_single(self, channel=None, max_vel=None, acc=None, verbose=False):
        """Set velocity parameters for a single channel.

        Args:
            channel (str or int, optional): Channel name or number. Defaults to None.
            max_vel (float or None, optional): Maximum velocity. Defaults to None.
            acc (float or None, optional): Acceleration. Defaults to None.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        chan_idx = self._get_channel_idx(channel)
        
        if max_vel is not None:
            if isinstance(max_vel, (int, float)):
                max_vel = Decimal(max_vel)
        else:
            max_vel = self.channels[chan_idx].GetVelocityParams().MaxVelocity  # If no max vel is given, take the one that is already set

        if acc is not None:
            if isinstance(acc, (int, float)):
                acc = Decimal(acc)
        else:
            acc = self.channels[chan_idx].GetVelocityParams().Acceleration  # If no acceleration is given, take the one that is already set

        try:
            self.channels[chan_idx].SetVelocityParams(max_vel, acc)
        except Exception as e:
            print(f"Exception setting velocity params for channel {channel}: {e}")
        
        if verbose:
            print(f'Velocity parameters for channel {channel} set at:\n',
                f'Max vel {str(self.channels[chan_idx].GetVelocityParams().MaxVelocity)} mm/s\n',
                f'Acceleration: {str(self.channels[chan_idx].GetVelocityParams().Acceleration)} mm/s2')
        return None


    def print_position(self):
        """Print the current position of the device."""
        print(f"Device position: channels {self.channel_names} - {self.get_position()} mm")
    
    def get_position_decimal(self, channel):
        """Get the current position of a single channel in Decimal.

        Args:
            channel (str or int): Channel name or number.

        Returns:
            Decimal: Current position of the channel.
        """
        return self.channels[self._get_channel_idx(channel)].Position


    def get_position_channel(self, channel, verbose=False):
        """Get the current position of a single channel.

        Args:
            channel (str or int): Channel name or number.
            verbose (bool, optional): Whether to print additional information. Defaults to False.

        Returns:
            Float: Current position of the channel.
        """
        pos = self._decimal_to_float(self.get_position_decimal(channel))
        if verbose:
            print(f"Channel {channel} is in position {pos} mm")
        return pos

    def get_velocity_params(self, channel, verbose=False):
        """Get the velocity parameters of a single channel.

        Args:
            channel (str or int): Channel name or number.
            verbose (bool, optional): Whether to print additional information. Defaults to False.

        Returns:
            tuple: Tuple of acceleration and maximum velocity.
        """
        velParams = self.channels[self._get_channel_idx(channel)].GetVelocityParams()
        if verbose:
            print(f"Channel {channel} velocity parameters are:\n")
            print(f"Acceleration: {velParams.Acceleration} mm/s2")
            print(f"MaxVelocity: {velParams.MaxVelocity} mm/s")
        return self._decimal_to_float(velParams.MaxVelocity), self._decimal_to_float(velParams.Acceleration)

    def get_position(self, verbose=False):
        """Get the current position of the device.

        Args:
            verbose (bool, optional): Whether to print additional information. Defaults to False.

        Returns:
            list: List of current positions for each channel.
        """
        pos = [self.get_position_channel(chan, verbose=verbose) for chan in self.channel_names]
        return pos

    def disconnect(self, verbose=False):
        """Disconnect the device.

        Args:
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        self.device.Disconnect()
        if verbose:
            print(f"Device {self.name} is DISCONNECTED")
        return None

    def finish(self, verbose=False):
        """Stop polling and disconnect the device.

        Args:
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
        self.stop_polling_channels(verbose=verbose)
        self.disconnect(verbose=verbose)

    def standard_initialize_channels(self, home=True, force_home=False, verbose=False):
        """Standard initialization of the channels.

        Args:
            force_home (bool, optional): Whether to force homing even if already homed. Defaults to False.
            verbose (bool, optional): Whether to print additional information. Defaults to False.
        """
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
        return channel.IsEnabled

    def channel_IsHomed(self, channel):
        """Determine whether this motor is homed.

        Args:
            channel (any): Channel object.

        Returns:
            bool: True if the channel is homed, False otherwise.
        """
        return channel.Status.IsHomed

    def channel_IsHoming(self, channel):
        """Determine whether this motor is homing.

        Args:
            channel (any): Channel object.

        Returns:
            bool: True if the channel is homing, False otherwise.
        """
        return channel.Status.IsHoming

    def channel_IsInMotion(self, channel):
        """Determine whether this motor is in motion.

        Args:
            channel (any): Channel object.

        Returns:
            bool: True if the channel is in motion, False otherwise.
        """
        return channel.Status.IsInMotion

    def channel_Position(self, channel):
        """Get the position in Real World Units.

        Args:
            channel (any): Channel object.

        Returns:
            Decimal: Current position in Real World Units.
        """
        return channel.Position

    def channel_Velocity(self, channel):
        """Get the current velocity.

        Args:
            channel (any): Channel object.

        Returns:
            float: Current velocity.
        """
        return channel.Status.Velocity

    def channel_IsSettled(self, channel):
        """Determine whether the device is in a settled state.

        Args:
            channel (any): Channel object.

        Returns:
            bool: True if the channel is settled, False otherwise.
        """
        return channel.Status.IsSettled
    
    def test_basic(self):
        """Test basic functionality of the device."""
        self.standard_initialize_channels(home=False, verbose=True)
        self.print_position()
        self.print_velocity_params()
        self.set_velocity_params(max_vel=200, acc=1100, verbose=True)
        self.print_velocity_params()
        self.print_position()
        self.finish(verbose=True)


if __name__ == '__main__':
    conn = BBD30XController(simulated=True, verbose=True, very_verbose=True)

    # # Test an alternative configuration
    # name = 'BBD30X'
    # conn = BBD30XController(
    #     name=name, simulated=True, verbose=True, very_verbose=True
    # )

    # conn.test_basic()
    # conn.moveTo([53.452546, 30.3564564], max_vel=10, acc=200, verbose=True)
    # conn.finish(verbose=True)
