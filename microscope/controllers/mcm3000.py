"""MCM3000Controller."""
import time
import serial
import warnings

supported_stages = {
    # 'Type': (+-stage_limit_um, stage_conversion_um)
    # from MCM300_Direct_Serial_Communication.pdf
    # The stage limit is set such that the allowed positions will be between
    # +stage_limit_um and -stage_limit_um
    'ZFM2020': {
        'limits': [-1e3 * 12.7, 1e3 * 12.7],
        'conversion': 0.2116667
    },
    # 'ZFM2030':(1e3 * 12.7, 0.2116667),
}


class MCM3000Controller:

    def __init__(
        self,
        # This is 'COMX' if using USB connection
        port,
        # Name on controller
        name='MCM3000',
        # Defines the name of the type of stages (i.e. 'ZFM2020')
        stages=3*(None,),
        # States if the axis are reversed (i.e. down is positive)
        reverse=3*(False,),
        # Label of each channel
        # WATCH OUT BECAUSE IN PRACTICE THEY ARE LABELLED 1, 2, 3
        channels=(1, 2, 3),
        # If True, info in printed in terminal
        verbose=True,
        # If True, more info in printed in terminal
        very_verbose=False,
        # If this is a simulated controller
        simulated=False
    ):
        self.name = name
        self.supported_stages = supported_stages
        self.verbose = verbose
        self.very_verbose = very_verbose
        if self.verbose:
            print(f'{self.name}: opening...', end='')
        if simulated:
            self.port = 'The port is simulated'
        else:
            try:
                self.port = serial.Serial(port=port, baudrate=460800)
            except serial.serialutil.SerialException:
                raise IOError(
                    f'{self.name}: no connection on port {port}'
                )
        if self.verbose:
            print('done.')
        assert type(stages) is tuple and type(reverse) is tuple and type(channels) is tuple, (f'{self.name}: stages, reverse and channels must be a tuple, currently {type(stages)}, {type(reverse)}, {type(channels)}')
        assert len(stages) == 3 and len(reverse) == 3 and len(channels) == 3, (f'{self.name}: stages, reverse and channels must be a tuple of 3 elements, currently {len(stages)}, {len(reverse)}, {len(channels)}')
        for element in reverse:
            assert type(element) == bool, (f'{self.name}: reverse must be a tuple of booleans')
        for element in stages: 
            if element is not None:
                assert element in self.supported_stages, (f'{self.name}: stage \'{element}\' not tested for {self.name} controller!!')
        self.stages = stages
        self.channels = channels
        # This is for internal use
        self._internal_channels = (0, 1, 2)
        # This is for internal use
        self._internal_channels_dict = dict(
            zip(self.channels, self._internal_channels)
        )
        self.reverse = reverse
        self.reverse_factors = len(reverse)*[1,]
        for ii in range(len(reverse)):
            if self.reverse[ii]:
                self.reverse_factors[ii] = -1
        # The lowest and highest range of the stage
        self._stage_upper_limit_um = 3*[None]
        self._stage_lower_limit_um = 3*[None]
        # The lowest and highest scan points (i.e. the lowest point before
        # damaging the sample being scanned)
        self._stage_lowest_scan_point_um = 3*[None]
        self._stage_highest_scan_point_um = 3*[None]
        # The level at which to retract before engaging in X-Y motion
        self._stage_retract_point_um = 3*[None]
        # The minimum number of counts that it can move (for very small motions
        # it struggles)
        self._min_encoder_motion = 5
        # Conversion factor: um/count
        self._stage_conversion_um = 3*[None]
        self._current_encoder_value = 3*[None]
        # Is None when all motions have finished but, while in motion, it is
        # the target encoder value (until it is reached and becomes None)
        self._pending_encoder_value = 3*[None]

        for channel, stage in enumerate(stages):
            if stage is not None:
                assert stage in self.supported_stages, (f'{self.name}: stage \'{stage}\' not supported')
                # Set lower and upper limit (these are the max and min points
                # that the stage can physically do)
                # Check that the limits are correctly set
                if self.supported_stages[stage]["limits"][0] == self.supported_stages[stage]["limits"][1]:
                    self.supported_stages[stage]["limits"][1] = abs(self.supported_stages[stage]["limits"][0])
                    self.supported_stages[stage]["limits"][0] = -abs(self.supported_stages[stage]["limits"][1])
                    warnings.warn(f'{self.name}: stage \'{stage}\' has the same upper and lower limits, assuming symmetric range')
                elif self.supported_stages[stage]["limits"][0] > self.supported_stages[stage]["limits"][1]:
                    buffer = self.supported_stages[stage]["limits"][0]
                    self.supported_stages[stage]["limits"][0] = self.supported_stages[stage]["limits"][1]
                    self.supported_stages[stage]["limits"][1] = buffer
                    warnings.warn(f'{self.name}: stage \'{stage}\' has the upper limit smaller than the lower limit, swapping them')
                self._stage_upper_limit_um[channel] = self.supported_stages[stage]["limits"][1]
                self._stage_lower_limit_um[channel] = self.supported_stages[stage]["limits"][0]
                # Set conversion factor
                self._stage_conversion_um[channel] = abs(self.supported_stages[stage]["conversion"]) # Just ensure that it is positive
                # Set scan points and retract points (for initializing they are just the same as max points)
                self._stage_highest_scan_point_um[channel] = self._stage_upper_limit_um[channel]
                self._stage_lowest_scan_point_um[channel] = self._stage_lower_limit_um[channel]
                # 10 um before the highest scan point
                self._stage_retract_point_um[channel] = self._stage_highest_scan_point_um[channel]-self._stage_conversion_um[channel]*10
                if simulated:
                    self._current_encoder_value[channel] = 'the encoder is simulated'
                else:
                    self._current_encoder_value[channel] = self._get_encoder_value(self.channels[self._internal_channels.index(channel)], True)

        if self.verbose:
            print(f'\n{self.name}: stages:', self.stages)
            print(f'\n{self.name}: channels:', self.channels)
            print(f'\n{self.name}: reverse:', self.reverse)
            print(f'\n{self.name}: reverse factors', self.reverse_factors)
            print(f'\n{self.name}: stage_upper_limit_um:', self._stage_upper_limit_um)
            print(f'\n{self.name}: stage_highest_scan_point_um:', self._stage_highest_scan_point_um)
            print(f'\n{self.name}: stage_lower_limit_um:', self._stage_lower_limit_um)
            print(f'\n{self.name}: stage_lowest_scan_point_um:', self._stage_lowest_scan_point_um)  
            print(f'\n{self.name}: stage_conversion_um:', self._stage_conversion_um)
            print(f'\n{self.name}: stage_retract_point_um:', self._stage_retract_point_um)
            print(f'\n{self.name}: current_encoder_value:', self._current_encoder_value)

    def print_info(self):
        """
        Prints the information about the controller and the stages.
        """
        print('\n---------------------')
        print('---------------------')
        print(f'Controller {self.name} info:')
        print(f'\n{self.name}: stages:', self.stages)
        print(f'\n{self.name}: channels:', self.channels)
        print(f'\n{self.name}: reverse:', self.reverse)
        print(f'\n{self.name}: reverse factors', self.reverse_factors)
        print(f'\n{self.name}: stage_upper_limit_um:', self._stage_upper_limit_um)
        print(f'\n{self.name}: stage_highest_scan_point_um:', self._stage_highest_scan_point_um)
        print(f'\n{self.name}: stage_lower_limit_um:', self._stage_lower_limit_um)
        print(f'\n{self.name}: stage_lowest_scan_point_um:', self._stage_lowest_scan_point_um)  
        print(f'\n{self.name}: stage_conversion_um:', self._stage_conversion_um)
        print(f'\n{self.name}: stage_retract_point_um:', self._stage_retract_point_um)
        print(f'\n{self.name}: current_encoder_value:', self._current_encoder_value)
        print('---------------------')
        print('---------------------\n')

    def print_channel_info(self, channel):
        """
        Prints the information about the specified channel.

        Args:
            channel (int): The channel to print the information for.
        """
        self.validate_channel(channel)
        print('\n---------------------')
        print('---------------------')
        print(f'Controller {self.name}, channel {channel} info:')
        print(f'\n{self.name}, channel {channel}: stage:', self.get_stages(channel))
        print(f'\n{self.name}, channel {channel}: reverse:', self.get_reverse(channel))
        print(f'\n{self.name}, channel {channel}: reverse factor:', self.get_reverse_factors(channel))
        print(f'\n{self.name}, channel {channel}: stage_upper_limit_um:', self.get_stage_upper_limit_um(channel))
        print(f'\n{self.name}, channel {channel}: stage_highest_scan_point_um:', self.get_stage_highest_scan_point_um(channel))
        print(f'\n{self.name}, channel {channel}: stage_lower_limit_um:', self.get_stage_lower_limit_um(channel))
        print(f'\n{self.name}, channel {channel}: stage_lowest_scan_point_um:', self.get_stage_lowest_scan_point_um(channel))  
        print(f'\n{self.name}, channel {channel}: stage_conversion_um:', self.get_stage_conversion_um(channel))
        print(f'\n{self.name}, channel {channel}: stage_retract_point_um:', self.get_stage_retract_point_um(channel))
        print(f'\n{self.name}, channel {channel}: current_encoder_value:', self.get_current_encoder_value(channel))
        print('---------------------')
        print('---------------------\n')

    def validate_channel(self, channel, internal=False):
        """
        Validates if the specified channel is available.

        Args:
            channel (str): The channel to validate.
            internal (bool, optional): If True, the channel is validated against internal channels. Defaults to False.

        Raises:
            AssertionError: If the specified channel is not available.
        """
        if not internal:
            assert channel in self.channels, (f'{self.name}: channel \'{channel}\' not available')
        else:
            assert channel in self._internal_channels, (f'{self.name}: channel \'{channel}\' not available')


    def get_stages(self, channel=None, internal=False):
        """
        Retrieves the stage names for a given channel or all channels.

        Args:
            channel (int or None, optional): The channel to retrieve the stage name for. If None, returns names for all channels.
            internal (bool, optional): If True, treats `channel` as an internal index. Otherwise, `channel` is treated as an external label.

        Returns:
            tuple or str: The stage name(s) for the requested channel(s).
        """
        if channel is None:
            return self.stages
        else:
            self.validate_channel(channel, internal)
            return self.stages[self._internal_channels_dict[channel]] if not internal else self.stages[channel]

    def get_channels(self):
        """
        Retrieves the labels of each control channel.

        Returns:
            tuple: The labels of the control channels.
        """
        return self.channels

    def get_reverse(self, channel=None, internal=False):
        """
        Retrieves the reverse motion direction indicator for a given channel or all channels.

        Args:
            channel (int or None, optional): The channel to retrieve the reverse indicator for. If None, returns indicators for all channels.
            internal (bool, optional): If True, treats `channel` as an internal index. Otherwise, `channel` is treated as an external label.

        Returns:
            tuple or bool: The reverse motion direction indicator(s) for the requested channel(s).
        """
        if channel is None:
            return self.reverse
        else:
            self.validate_channel(channel, internal)
            return self.reverse[self._internal_channels_dict[channel]] if not internal else self.reverse[channel]

    def get_reverse_factors(self, channel=None, internal=False):
        """
        Retrieves the reverse factors for a given channel or all channels.

        Args:
            channel (int or None, optional): The channel to retrieve the reverse factor for. If None, returns factors for all channels.
            internal (bool, optional): If True, treats `channel` as an internal index. Otherwise, `channel` is treated as an external label.

        Returns:
            list or int: The reverse factor(s) for the requested channel(s).
        """
        if channel is None:
            return self.reverse_factors
        else:
            self.validate_channel(channel, internal)
            return self.reverse_factors[self._internal_channels_dict[channel]] if not internal else self.reverse_factors[channel]

    def get_current_encoder_value(self, channel=None, internal=False):
        """
        Retrieves the current encoder values for a given channel or all channels.

        Args:
            channel (int or None, optional): The channel to retrieve the encoder value for. If None, returns values for all channels.
            internal (bool, optional): If True, treats `channel` as an internal index. Otherwise, `channel` is treated as an external label.

        Returns:
            list or int: The current encoder value(s) for the requested channel(s).
        """
        if channel is None:
            return self._current_encoder_value
        else:
            self.validate_channel(channel, internal)
            return self._current_encoder_value[self._internal_channels_dict[channel]] if not internal else self._current_encoder_value[channel]
            

    def get_stage_upper_limit_um(self, channel=None, internal=False):
        """
        Retrieves the upper motion limit for a given channel or all channels.

        Args:
            channel (int or None, optional): The channel to retrieve the upper motion limit for. If None, returns limits for all channels.
            internal (bool, optional): If True, treats `channel` as an internal index. Otherwise, `channel` is treated as an external label.

        Returns:
            list or int: The upper motion limit(s) in micrometers for the requested channel(s).
        """
        if channel is None:
            return self._stage_upper_limit_um
        else:
            self.validate_channel(channel, internal)
            return self._stage_upper_limit_um[self._internal_channels_dict[channel]] if not internal else self._stage_upper_limit_um[channel]

    def get_stage_lower_limit_um(self, channel=None, internal=False):
        """
        Retrieves the lower motion limit for a given channel or all channels.

        Args:
            channel (int or None, optional): The channel to retrieve the lower motion limit for. If None, returns limits for all channels.
            internal (bool, optional): If True, treats `channel` as an internal index. Otherwise, `channel` is treated as an external label.

        Returns:
            list or int: The lower motion limit(s) in micrometers for the requested channel(s).
        """
        if channel is None:
            return self._stage_lower_limit_um
        else:
            self.validate_channel(channel, internal)
            return self._stage_lower_limit_um[self._internal_channels_dict[channel]] if not internal else self._stage_lower_limit_um[channel]

    def get_stage_lowest_scan_point_um(self, channel=None, internal=False):
        """
        Retrieves the safe lower bound for scanning to avoid damaging the sample, for a given channel or all channels.

        Args:
            channel (int or None, optional): The channel to retrieve the safe lower scan point for. If None, returns scan points for all channels.
            internal (bool, optional): If True, treats `channel` as an internal index. Otherwise, `channel` is treated as an external label.

        Returns:
            list or int: The safe lower scan point(s) in micrometers for the requested channel(s).
        """
        if channel is None:
            return self._stage_lowest_scan_point_um
        else:
            self.validate_channel(channel, internal)
            return self._stage_lowest_scan_point_um[self._internal_channels_dict[channel]] if not internal else self._stage_lowest_scan_point_um[channel]

    def get_stage_highest_scan_point_um(self, channel=None, internal=False):
        """
        Retrieves the safe upper bound for scanning, for a given channel or all channels.

        Args:
            channel (int or None, optional): The channel to retrieve the safe upper scan point for. If None, returns scan points for all channels.
            internal (bool, optional): If True, treats `channel` as an internal index. Otherwise, `channel` is treated as an external label.

        Returns:
            list or int: The safe upper scan point(s) in micrometers for the requested channel(s).
        """
        if channel is None:
            return self._stage_highest_scan_point_um
        else:
            self.validate_channel(channel, internal)
            return self._stage_highest_scan_point_um[self._internal_channels_dict[channel]] if not internal else self._stage_highest_scan_point_um[channel]
        

    def get_stage_retract_point_um(self, channel=None, internal=False):
        """
        Retrieves the retract points before engaging in X-Y motion, for a given channel or all channels.

        Args:
            channel (int or None, optional): The channel to retrieve the retract point for. If None, returns retract points for all channels.
            internal (bool, optional): If True, treats `channel` as an internal index. Otherwise, `channel` is treated as an external label.

        Returns:
            list or int: The retract point(s) in micrometers for the requested channel(s).
        """
        if channel is None:
            return self._stage_retract_point_um
        else:
            self.validate_channel(channel, internal)
            return self._stage_retract_point_um[self._internal_channels_dict[channel]] if not internal else self._stage_retract_point_um[channel]

    def get_min_encoder_motion(self):
        """
        Retrieves the minimum number of encoder counts required for motion to be recognized.

        Returns:
            int: The minimum number of encoder counts.
        """
        return self._min_encoder_motion

    def get_stage_conversion_um(self, channel=None, internal=False):
        """
        Retrieves the conversion factors from encoder counts to micrometers for each stage, for a given channel or all channels.

        Args:
            channel (int or None, optional): The channel to retrieve the conversion factor for. If None, returns conversion factors for all channels.
            internal (bool, optional): If True, treats `channel` as an internal index. Otherwise, `channel` is treated as an external label.

        Returns:
            list or int: The conversion factor(s) for the requested channel(s).
        """
        if channel is None:
            return self._stage_conversion_um
        else:
            self.validate_channel(channel, internal)
            return self._stage_conversion_um[self._internal_channels_dict[channel]] if not internal else self._stage_conversion_um[channel]

    def get_pending_encoder_value(self, channel=None, internal=False):
        """
        Retrieves the target encoder values during motion, which becomes None when motion finishes, for a given channel or all channels.

        Args:
            channel (int or None, optional): The channel to retrieve the target encoder value for. If None, returns target values for all channels.
            internal (bool, optional): If True, treats `channel` as an internal index. Otherwise, `channel` is treated as an external label.

        Returns:
            list or int or None: The target encoder value(s) for the requested channel(s), or None if motion has finished.
        """
        if channel is None:
            return self._pending_encoder_value
        else:
            self.validate_channel(channel, internal)
            return self._pending_encoder_value[self._internal_channels_dict[channel]] if not internal else self._pending_encoder_value[channel]

    def _send(self, cmd, channel, response_bytes=None):
        """
        Sends a command to a specific channel of the motor controller.

        This method sends a command to the motor controller associated with a specific
        channel and optionally reads a response. It checks if the stage for the given
        channel is initialized before sending the command.

        Args:
            cmd (bytes): The command to be sent to the motor controller.
            channel (int): The channel to which the command is sent.
            response_bytes (int, optional): The number of bytes to read from the response. If None, no response is read.

        Returns:
            bytes or None: The response from the controller if `response_bytes` is not None, otherwise None.

        Raises:
            AssertionError: If the stage for the specified channel is not initialized.
        """
        assert self.stages[self._internal_channels_dict[channel]] is not None, (f'{self.name}: channel {channel}: stage = None (cannot send command)')
        self.port.write(cmd)
        if response_bytes is not None:
            response = self.port.read(response_bytes)
        else:
            response = None
        assert self.port.inWaiting() == 0
        return response

    def _get_encoder_value(self, channel, verbose=False):
        """
        Retrieves the current encoder value for a specified channel.

        This method sends a command to the motor controller to get the current encoder
        value of the stage associated with the specified channel. It validates if the
        channel is available and ensures that the response is correctly associated with
        the requested channel before returning the encoder value.

        Args:
            channel (int): The channel from which to retrieve the encoder value.
            verbose (bool, optional): If True, prints the retrieved encoder value to the terminal. Defaults to False.

        Returns:
            int: The current encoder value for the specified channel.

        Raises:
            AssertionError: If the specified channel is not available.
        """
        assert channel in self.channels, (f'{self.name}: channel \'{channel}\' not available')
        channel_byte = self._internal_channels_dict[channel].to_bytes(1, byteorder='little')
        cmd = b'\x0a\x04' + channel_byte + b'\x00\x00\x00'
        response = self._send(cmd, channel, response_bytes=12)
        assert response[6:7] == channel_byte # channel = selected
        encoder_value = int.from_bytes(
            response[-4:], byteorder='little', signed=True)
        if verbose:
            print(f'\n{self.name}: ch{channel} -> stage encoder value = {encoder_value}')
        return encoder_value

    def _reverse_limit_signs(self, channel):
        """
        Reverses the sign of the motion limit values for a specified channel.

        This method modifies the upper and lower motion limit values, along with the
        highest and lowest scan point values, and the retract point value for the
        specified channel by reversing their signs. This is useful in scenarios where
        the direction of motion needs to be inverted.

        Args:
            channel (int): The channel for which to reverse the limit signs.

        Raises:
            AssertionError: If the specified channel is not available.
        """
        assert channel in self.channels, (f'{self.name}: channel \'{channel}\' not available')
        # Set lower and upper limit (these are the max and min points that the stage can physically do)
        self._stage_upper_limit_um[self._internal_channels_dict[channel]] = -self._stage_upper_limit_um[self._internal_channels_dict[channel]]
        self._stage_lower_limit_um[self._internal_channels_dict[channel]] = -self._stage_lower_limit_um[self._internal_channels_dict[channel]]
        # Set scan points and retract points (for initializing they are just the same as max points)
        self._stage_highest_scan_point_um[self._internal_channels_dict[channel]] = -self._stage_highest_scan_point_um[self._internal_channels_dict[channel]]
        self._stage_lowest_scan_point_um[self._internal_channels_dict[channel]] = -self._stage_lowest_scan_point_um[self._internal_channels_dict[channel]]
        self._stage_retract_point_um[self._internal_channels_dict[channel]] = -self._stage_retract_point_um[self._internal_channels_dict[channel]]


    def _set_encoder_value_to_zero(self, channel):
        """
        Sets the current position as zero for the encoder count on a specified channel.

        This method resets the encoder value to zero for the given channel, effectively
        recalibrating the position measurement. It warns that after zeroing, the limits
        are no longer valid and should be reset unless the zeroing is done at the center
        of its range. The method waits until the encoder value is confirmed to be reset
        to zero before returning.

        Args:
            channel (int): The channel for which to set the encoder value to zero.

        Returns:
            None

        Raises:
            AssertionError: If the specified channel is not available.
        
        Note:
            After zeroing, it's essential to reset the motion limits, unless the zeroing
            operation was performed at the center of the stage's range.
        """
        assert channel in self.channels, (f'{self.name}: channel \'{channel}\' not available')
        if self.verbose:
            encoder_value = self._get_encoder_value(channel, verbose = self.verbose)
        channel_byte = self._internal_channels_dict[channel].to_bytes(2, byteorder='little')
        encoder_bytes = (0).to_bytes(4, 'little', signed=True) # set to zero
        cmd = b'\x09\x04\x06\x00\x00\x00' + channel_byte + encoder_bytes
        self._send(cmd, channel)
        if self.verbose:
            print(f'{self.name}: ch{channel} -> waiting for re-set to zero')
        while True:
            if self._get_encoder_value(channel, verbose=self.verbose) == 0: break
        self._current_encoder_value[self._internal_channels_dict[channel]] = 0
        if self.verbose:
            print(f'{self.name}: ch{channel} -> done with encoder re-set')
        return None

    def _move_to_encoder_value(self, channel, encoder_value, block=True):
        """
        Moves the stage encoder to the specified value for the given channel.

        Args:
            channel (str): The channel to move the stage encoder for.
            encoder_value (int): The value to move the stage encoder to.
            block (bool, optional): Whether to block until the move is finished. Defaults to True.

        Returns:
            None
        """
        assert channel in self.channels, (f'{self.name}: channel \'{channel}\' not available')
        if self._pending_encoder_value[self._internal_channels_dict[channel]] is not None:
            self._finish_move(channel)
        encoder_bytes = encoder_value.to_bytes(4, 'little', signed=True)
        channel_bytes = self._internal_channels_dict[channel].to_bytes(2, byteorder='little')
        cmd = b'\x53\x04\x06\x00\x00\x00' + channel_bytes + encoder_bytes
        self._send(cmd, channel)
        self._pending_encoder_value[self._internal_channels_dict[channel]] = encoder_value
        if self.very_verbose:
            print(f'{self.name}: ch{channel} -> moving stage encoder to value = {encoder_value}')
        if block:
            self._finish_move(channel)
        return None

    def _finish_move(self, channel, polling_wait_s=0.1, verbose=False):
        """
        Finish the movement of the specified channel and update the current encoder value and position.

        Args:
            channel (str): The channel to finish the movement for.
            polling_wait_s (float, optional): The time to wait between polling the encoder value. Defaults to 0.1.
            verbose (bool, optional): Whether to print verbose output. Defaults to False.

        Returns:
            tuple: A tuple containing the current encoder value and the current position in um.
        """
        assert channel in self.channels, (f'{self.name}: channel \'{channel}\' not available')
        if self._pending_encoder_value[self._internal_channels_dict[channel]] is None:
            return
        current_encoder_value = self._get_encoder_value(channel, verbose = False)
        timeout = time.time() + 6 # 6s timeout, measured to be max time between top and bottom motions
        while True:
            if current_encoder_value == self._pending_encoder_value[self._internal_channels_dict[channel]]: #FIRST VERSION
            # if abs(current_encoder_value - self._pending_encoder_value[self._internal_channels_dict[channel]]) <= 1 : # Check that error is smaller than resolution (i.e. one encoder value)
                break
            if time.time() > timeout:
                print(f"\033[93m\nMCM3000 motion timed out\033[0m") # TODO double check requirements that is close enough
                position_error = current_encoder_value - self._pending_encoder_value[self._internal_channels_dict[channel]] # position error in enconder counts
                if abs(position_error) > 1:
                    print(f"\033[91m\nMCM3000 position error: {position_error} counts \033[0m")
                break
            if verbose: print('.', end='')
            time.sleep(polling_wait_s)
            current_encoder_value = self._get_encoder_value(channel, verbose = False)
        self._current_encoder_value[self._internal_channels_dict[channel]] = current_encoder_value
        current_position_um = self._um_from_encoder_value(
            channel, current_encoder_value)
        if verbose:
            print(f'\n{self.name}: ch{channel} -> finished moving to position_um = {current_position_um}')
        self._pending_encoder_value[self._internal_channels_dict[channel]] = None
        return current_encoder_value, current_position_um

    def _um_from_encoder_value(self, channel, encoder_value):
        """
        Converts the encoder value to micrometers (um) based on the channel and the stage conversion factor.

        Args:
            channel (str): The channel of the encoder value.
            encoder_value (float): The encoder value to be converted.

        Returns:
            float: The converted value in micrometers (um).
        """
        um = encoder_value * self._stage_conversion_um[self._internal_channels_dict[channel]]
        if self.reverse[self._internal_channels_dict[channel]]:
            um = -um
        return um + 0  # avoid -0.0

    def _encoder_value_from_um(self, channel, um):
        """
        Converts a distance in micrometers (um) to the corresponding encoder value for the specified channel.

        Args:
            channel (str): The channel for which to calculate the encoder value.
            um (float): The distance in micrometers to convert.

        Returns:
            int: The encoder value corresponding to the given distance in micrometers.
        """
        encoder_value = int(um / self._stage_conversion_um[self._internal_channels_dict[channel]])
        if self.reverse[self._internal_channels_dict[channel]]:
            encoder_value = -encoder_value
        return encoder_value + 0  # avoid -0.0

    def _check_min_motion(self, channel, target_encoder_value):
        """
        Check if the desired motion is smaller than the minimum motion and, if so, move out to be able to move back in.

        Args:
            channel (str): The channel to check the motion for.
            target_encoder_value (float): The target encoder value to check against.

        Returns:
            bool: True if it is necessary to move, False otherwise.
        """

        if self._pending_encoder_value[self._internal_channels_dict[channel]]:
            if target_encoder_value == self._pending_encoder_value[self._internal_channels_dict[channel]]:
                print(f"MCM3000: ch{channel} -> motion already in progress")
                return False
            elif abs(target_encoder_value - self._pending_encoder_value[self._internal_channels_dict[channel]]) <= self._min_encoder_motion:
                self.move_um(channel, 10, relative=True, block=True, verbose=False)
        else:
            if target_encoder_value == self._current_encoder_value[self._internal_channels_dict[channel]]:
                print(f"{self.name}: ch{channel} -> already at position")
                return False
            elif abs(target_encoder_value - self._current_encoder_value[self._internal_channels_dict[channel]]) <= self._min_encoder_motion:
                self.move_um(channel, 10, relative=True, block=True, verbose=False)
        return True


    def get_position_um(self, channel, verbose=False):
        """
        Get the position in micrometers (um) for the specified channel.

        Args:
            channel (str): The channel for which to get the position.
            verbose (bool, optional): If True, print the stage position in micrometers. Defaults to False.

        Returns:
            float: The stage position in micrometers.

        Raises:
            AssertionError: If the specified channel is not available.
        """
        assert channel in self.channels, (f'{self.name}: channel \'{channel}\' not available')
        encoder_value = self._get_encoder_value(channel, verbose=False)
        position_um = self._um_from_encoder_value(channel, encoder_value)
        if verbose:
            print(f'{self.name}: ch{channel} -> stage position_um = {position_um}')
        return position_um

    def set_stage_limit_um(self, channel, limit_um=None, lower_limit=True):
        """
        Set the limit of a stage motion for a specified channel.

        Args:
            channel (str): The channel for which to set the limit.
            limit_um (float, optional): The limit value in micrometers. If not provided, the current position is used.
            lower_limit (bool, optional): Whether to set the lower limit or the upper limit. Defaults to True.

        Returns:
            float: The target limit value in micrometers.
        """
        assert channel in self.channels, (f'{self.name}: channel \'{channel}\' not available')
        # Set the limit of a stage motion for a specified channel
        if limit_um:
            target_limit_um = limit_um
        else:
            target_limit_um = self.get_position_um(channel, verbose = self.very_verbose)
        assert self._stage_lower_limit_um[self._internal_channels_dict[channel]] <= target_limit_um <= self._stage_upper_limit_um[self._internal_channels_dict[channel]], (
                f'{self.name}: ch{channel} -> requested limit ({target_limit_um}) exceeds the stage limits ([{self._stage_lower_limit_um[self._internal_channels_dict[channel]]},{self._stage_upper_limit_um[self._internal_channels_dict[channel]]}])')
        if lower_limit:
            self._stage_lowest_scan_point_um[self._internal_channels_dict[channel]] = target_limit_um
            if self.verbose:
                print(f'{self.name}: ch{channel} -> stage lowest scan point set to: {target_limit_um} um' )
        else:
            self._stage_highest_scan_point_um[self._internal_channels_dict[channel]] = target_limit_um
            if self.verbose:
                print(f'{self.name}: ch{channel} -> stage highest scan point set to: {target_limit_um} um' )
            if self._stage_retract_point_um[self._internal_channels_dict[channel]] > self._stage_highest_scan_point_um[self._internal_channels_dict[channel]]:
                    self.set_retract_point_um(channel, self._stage_highest_scan_point_um[self._internal_channels_dict[channel]])
        return target_limit_um
    
    
    def get_retract_point_um(self, channel, verbose=False):
        """
        Get the stage retract point in micrometers for the specified channel.

        Parameters:
            channel (str): The channel for which to retrieve the stage retract point.
            verbose (bool): If True, print the stage retract point to the console.

        Returns:
            float: The stage retract point in micrometers for the specified channel.
        """
        assert channel in self.channels, (f'{self.name}: channel \'{channel}\' not available')
        if verbose:
            print(f'{self.name}: ch{channel} -> stage retract point = {self._stage_retract_point_um[self._internal_channels_dict[channel]]} um')
        return self._stage_retract_point_um[self._internal_channels_dict[channel]]

    def set_retract_point_um(self, channel, retract_pos_um=None, relative=False, verbose=False):
        """
        Set the retract position of a stage motion for a specified channel.

        Args:
            channel (str): The channel for which to set the retract position.
            retract_pos_um (float, optional): The retract position in micrometers. If not provided, the current position will be used.
            relative (bool, optional): Whether the retract position is relative to the current position. Default is False.
            verbose (bool, optional): Whether to print verbose output. Default is False.

        Returns:
            float: The target retract position in micrometers.
        """
        assert channel in self.channels, (f'{self.name}: channel \'{channel}\' not available')
        # Set the retract position of a stage motion for a specified channel
        if retract_pos_um:
            target_retract_um = retract_pos_um
            if relative:
                target_retract_um = target_retract_um + self.get_position_um(channel)
        else:
            target_retract_um = self.get_position_um(channel)
        assert self._stage_lowest_scan_point_um[self._internal_channels_dict[channel]] <= target_retract_um <= self._stage_highest_scan_point_um[self._internal_channels_dict[channel]],( 
            f'{self.name}: ch{channel} -> requested retract point ({target_retract_um}) exceeds the stage limits ([{self._stage_lowest_scan_point_um[self._internal_channels_dict[channel]]},{self._stage_highest_scan_point_um[self._internal_channels_dict[channel]]}])')
        self._stage_retract_point_um[self._internal_channels_dict[channel]] = target_retract_um
        if verbose:
            print(f'{self.name}: ch{channel} -> stage retract point set to: {target_retract_um} um' )
        return target_retract_um

    def legalize_move_um(self, channel, move_um, relative=True, verbose=True):
        """
        Checks if the desired motion is within the accepted boundaries and returns the legalized move in micrometers (um).
        
        Args:
            channel (str): The channel to perform the motion on.
            move_um (float): The desired motion in micrometers (um).
            relative (bool, optional): Whether the motion is relative or absolute. Defaults to True.
            verbose (bool, optional): Whether to print verbose output. Defaults to True.
        
        Returns:
            float: The legalized move in micrometers (um) if it is within the boundaries, None otherwise.
        """
        assert channel in self.channels, (f'{self.name}: channel \'{channel}\' not available')
        target_encoder_value = self._encoder_value_from_um(channel, move_um)
        if relative:
            if self._pending_encoder_value[self._internal_channels_dict[channel]]:
                target_encoder_value += self._pending_encoder_value[self._internal_channels_dict[channel]]
            else:
                target_encoder_value += self._current_encoder_value[self._internal_channels_dict[channel]]
        # Check that want to move beyond the minimum number of counts and, if not, do the motion back and forth
        if not self._check_min_motion(channel, target_encoder_value): return None
        # Set the target motion in um
        target_move_um = self._um_from_encoder_value(channel, target_encoder_value) # This might produce a slight difference between move_un and target, due to the need to have an encoder value, but since afterwards it checks if the error is smaller than the resolution, all good
        # Check if there is a lowest scanning point, if not it refers to the limit
        if self._stage_lowest_scan_point_um[self._internal_channels_dict[channel]]:
            lower_limit_um = self._stage_lowest_scan_point_um[self._internal_channels_dict[channel]]
        else:
            lower_limit_um = self._stage_lower_limit_um[self._internal_channels_dict[channel]]
        # Check if there is a highest scanning point, if not it refers to the limit
        if self._stage_highest_scan_point_um[self._internal_channels_dict[channel]]:
            upper_limit_um = self._stage_highest_scan_point_um[self._internal_channels_dict[channel]]
        else:
            upper_limit_um = self._stage_upper_limit_um[self._internal_channels_dict[channel]]
        # Check that value is within boundaries
        assert lower_limit_um <= target_move_um <= upper_limit_um, (
                f'{self.name}: ch{channel} -> requested move_um ({target_move_um}) exceeds the limit_um ([{lower_limit_um},{upper_limit_um}])')
        legal_move_um = target_move_um
        if verbose:
            print(f'{self.name}: ch{channel} -> legalized move_um = {legal_move_um}'  +
                  f'({move_um} requested, relative={relative})')
        return legal_move_um

    def move_um(self, channel, move_um, relative=True, block=True, verbose=False):
        """
        Moves the specified channel by the given distance in micrometers.

        Args:
            channel (str): The channel to move.
            move_um (float): The distance to move in micrometers.
            relative (bool, optional): If True, the movement is relative to the current position. If False, the movement is absolute. Defaults to True.
            block (bool, optional): If True, the method blocks until the movement is completed. If False, the method returns immediately. Defaults to True.
            verbose (bool, optional): If True, additional information about the movement is printed. Defaults to False.

        Returns:
            float: The actual distance moved in micrometers.

        Raises:
            AssertionError: If the specified channel is not available.

        """
        assert channel in self.channels, (f'{self.name}: channel \'{channel}\' not available')
        legal_move_um = self.legalize_move_um(channel, move_um, relative, verbose=verbose)
        if legal_move_um is None: # If there is no need to move
            if self.verbose:
                print(f'No need to move, already in position {self.get_position_um(channel, verbose = False)} um ({move_um} um was requested))')
            return
        if self.verbose:
            print(f'{self.name}: ch{channel} -> moving to position_um = {legal_move_um}', end='\n')
        encoder_value = self._encoder_value_from_um(channel, legal_move_um)
        self._move_to_encoder_value(channel, encoder_value, block)
        if block:
            self._finish_move(channel, verbose=verbose)
        else:
            print('\n')
        if verbose:
            print(f"Channel {channel} in position {self.get_position_um(channel, False)}")
        return legal_move_um

    def move_zero(self, channel, block=True):
        """
        Moves the specified channel to the zero position.

        Args:
            channel (str): The channel to move to zero.
            block (bool, optional): Whether to block until the movement is complete. Defaults to True.

        Returns:
            bool: True if the movement was successful, False otherwise.
        """
        assert channel in self.channels, (f'{self.name}: channel \'{channel}\' not available')
        if self.verbose:
            print(f'{self.name}: ch{channel} -> Moving to Zero', end='\n')
        return self.move_um(channel, 0.00, relative=False, block=block)

    def retract(self, channel):
        """
        Retracts the specified channel of the MCM3000 controller.

        Args:
            channel (str): The channel to retract.

        Raises:
            AssertionError: If the specified channel is not available.

        """
        assert channel in self.channels, (f'{self.name}: channel \'{channel}\' not available')
        if self.verbose:
            print(f'{self.name}: ch{channel} -> Moving to RETRACT position', end='\n')
        self.move_um(channel, self._stage_retract_point_um[self._internal_channels_dict[channel]], relative=False)

    def close(self, verbose=False, simulated=False):
        """
        Closes the connection to the MCM3000 controller.

        This method closes the connection to the MCM3000 controller by closing the port.
        """
        if verbose:
            print(f'{self.name}: closing...', end=' ')
        if not simulated:
            self.port.close()
        if verbose:
            print(f"{self.name} CLOSED.")
        return None


if __name__ == '__main__':
    # Remember starts at 1
    chnl = 1
    stage_controller = MCM3000Controller(
        'COM3',
        stages=('ZFM2020', None, None),
        reverse=(True, False, False),
        simulated=True
    )

    stage_controller.print_info()
    stage_controller.print_channel_info(chnl)

    # # Read position
    # print('\n# Get position:')
    # stage_pos = stage_controller.get_position_um(chnl, verbose=True)

    # # Test move to 0
    # if not True:
    #     print('\n# Moving to Zero:')
    #     stage_controller.move_zero(chnl)

    # # Test retract
    # if not True:
    #     stage_controller.retract(chnl)

    # #Test move absolute
    # if not True:
    #     target_um = +8000
    #     stage_controller.move_um(chnl, target_um, relative=False, verbose=True)

    # # Move relative position step is step_um
    # if not True:
    #     print('\n# Relative moves:')
    #     step_um = 1000 # um of each step
    #     move = stage_controller.move_um(chnl, step_um)
    #     move = stage_controller.move_um(chnl, -step_um)

    # # Test small motions
    # if not True:
    #     print('\n# Small moves:')
    #     stage_controller.move_um(chnl, stage_controller.get_position_um(chnl), relative=False, verbose=True)
    #     stage_controller.move_um(chnl, stage_controller.get_position_um(chnl)+0.55*stage_controller.get_stage_conversion_um(chnl), relative=False, verbose=True)

    # # Move relative position, n_steps up and down, each step is step_um
    # if not True:
    #     print('\n# Some relative moves:')
    #     step_num = 3 # number of steps
    #     step_um = 10 # um of each step
    #     for moves in range(3):
    #         move = stage_controller.move_um(chnl, step_um)
    #     for moves in range(3):
    #         move = stage_controller.move_um(chnl, -step_um)

    # # Position motion test
    # if not True:
    #     pos_test_um = 3900
    #     pos_test_rel = False
    #     print('\n# Legalized move:')
    #     legal_move_um = stage_controller.legalize_move_um(chnl, pos_test_um, relative = pos_test_rel)
    #     print(legal_move_um)
    #     stage_controller.move_um(chnl, pos_test_um, relative = pos_test_rel)
    #     print('\n# Get position:')
    #     stage_controller.get_position_um(chnl, verbose=True)

    # # Set limits test
    # if not True:
    #     print('\n# Set limits:')
    #     upper_lim_test_um = stage_controller.get_stage_upper_limit_um(chnl)/10
    #     lower_lim_test_um = stage_controller.get_stage_lower_limit_um(chnl)/10

    #     stage_controller.move_um(chnl, upper_lim_test_um, relative=False)
    #     stage_controller.set_stage_limit_um(chnl, lower_limit=False)

    #     stage_controller.move_um(chnl, lower_lim_test_um, relative=False)
    #     stage_controller.set_stage_limit_um(chnl, lower_limit=True)

    #     try:
    #         stage_controller.legalize_move_um(chnl, 2 * upper_lim_test_um, relative=False)
    #         print('Test 1 fail...Expected AssertionError was not raised.')
    #     except AssertionError as e:
    #         print('Test 1 pass...AssertionError was raised as expected.')

    #     try:
    #         stage_controller.legalize_move_um(chnl, 2 * lower_lim_test_um, relative=False)
    #         print('Test 2 fail...Expected AssertionError was not raised.')
    #     except AssertionError as e:
    #         print('Test 2 pass...AssertionError was raised as expected.')

    #     print(f'Test 3 pass...{isinstance(stage_controller.legalize_move_um(chnl, upper_lim_test_um / 2, relative=False), float)}')  # Should work
    #     print(f'Test 4 pass...{isinstance(stage_controller.legalize_move_um(chnl, lower_lim_test_um / 2, relative=False), float)}')  # Should work

    # # Set retract and test
    # if not True:
    #     print('\n# Set retract:')
    #     retract_point_test_um = stage_controller.get_stage_upper_limit_um(chnl)/12
    #     stage_controller.move_um(chnl, retract_point_test_um, relative=False)
    #     stage_controller.set_retract_point_um(chnl, retract_pos_um=None)

    #     stage_controller.move_zero(chnl)

    #     stage_controller.retract(chnl)

    # # re-set zero:
    # if not True:
    #     stage_controller.move_um(channel=chnl, move_um=8000, relative=False, verbose=True)
    #     stage_controller._set_encoder_value_to_zero(channel=chnl)
    #     stage_controller.move_um(channel=chnl, move_um=0, relative=False, verbose=True)

    # # Test motion time from the limits
    # if not True:
    #     from datetime import datetime
    #     print(f'Stage Lower Limit: {stage_controller.get_stage_lower_limit_um(chnl)} um')
    #     print(f'Stage Upper Limit: {stage_controller.get_stage_upper_limit_um(chnl)} um')
    #     while True:
    #         response = input("\033[93mIs this ok and in the path clear? (y/q)\033[0m")
    #         if response.lower().strip() == 'y':
    #             for i in range(10):
    #                 stage_controller.move_um(channel=chnl, move_um=-stage_controller.get_stage_lower_limit_um(chnl), relative=False,
    #                                         verbose=True)
    #                 time.sleep(2)
    #                 move_start_time = datetime.now()
    #                 stage_controller.move_um(channel=chnl, move_um=-stage_controller.get_stage_upper_limit_um(chnl), relative=False,
    #                                         verbose=True)
    #                 move_elapsed_time = datetime.now() - move_start_time
    #                 move_elapsed_seconds = move_elapsed_time.total_seconds()
    #                 print(f'Motion finished in {move_elapsed_time.total_seconds()} s')
    #             break
    #         elif response.lower().strip() == 'q':
    #             break
    #         else:
    #             print('Incorrect input, please reply: (y/q).')

    # stage_controller.close()
