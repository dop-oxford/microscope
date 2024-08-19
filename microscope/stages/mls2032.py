"""
A microscope interface to Thorlabs MLS203-2 stages.

https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=5360
"""
import microscope.abc
import typing


class MLS2032StageAxis(microscope.abc.StageAxis):
    """
    Instantiate an axis of a MLS203-2 stage.
    """

    def __init__(
        self, controller, axis: str, simulated=False, verbose=False
    ) -> None:
        if verbose:
            print('Initialising stage axis', axis)
        super().__init__()
        self.controller = controller
        self.axis = axis
        self.simulated = simulated

        # Not a good solution as min/max are used to build the stage map in
        # Mosaic, etc
        self.min_limit = 0.0
        self.max_limit = 100000.0

    def convert_to_mm(self, value, unit):
        """Convert a given value from specified units to millimetres (mm)."""
        # Dictionary to map units to their conversion factor to micrometers
        unit_conversion = {
            'um': 1e-3,
            'mm': 1,
            'cm': 10,
            'm': 1e3,
            'nm': 1e-6,
            'pm': 1e-9
        }
        if unit not in unit_conversion:
            raise ValueError(
                f"Unsupported unit: {unit}. Supported units are 'um', 'mm', "
                "'cm', 'm', 'nm', 'pm'."
            )
        # Perform conversion
        converted_value = value * unit_conversion[unit]

        return converted_value

    def move_by(self, delta: float, verbose=False) -> None:
        """Move by the specified distance."""
        if verbose:
            print(f'Moving stage axis {self.axis} by {delta}')
        relative = True
        self.move(delta, relative)

    def move_to(self, pos: float, verbose=False) -> None:
        """Move to the specified position."""
        if verbose:
            print(f'Moving stage axis {self.axis} to {pos}')
        relative = False
        self.move(pos, relative)

    def move(self, target_pos, relative, units='mm', verbose=False):
        """Move the stage axis to a specified end position."""
        target_mm_pos = self.convert_to_mm(target_pos, units)
        self.move_mm(target_mm_pos, relative, verbose)

    def move_mm(self, target_pos, relative=False, verbose=False):
        """Moves the stage axis to a specified end position."""
        if self.controller:
            self.controller.moveTo(
                self, target_pos, relative=relative, verbose=verbose
            )

    @property
    def position(self) -> float:
        if self.controller:
            if self.controller.is_busy():
                self.controller.wait_until_idle()
            return float(self.controller.get_absolute_position(self._axis))

    @property
    def limits(self) -> microscope.AxisLimits:
        return microscope.AxisLimits(
            lower=self.min_limit, upper=self.max_limit
        )


class MLS2032Stage(microscope.abc.Stage):
    """
    Instantiate a Thorlabs MLS203-2 stage.
    """

    def __init__(
        self, config, controller=None, simulated=False, verbose=False
    ):
        """Constructor method."""
        # Initialize the base class (Stage), which also handles Device
        super().__init__()

        self.stage_name = config.get('name', 'XY Stage')

        self.controller = controller
        if self.controller is not None:
            self.controller.__init__(config)
        else:
            print('A controller is not present.')
            print('The stage is initialising without a controller.')

        self.simulated = simulated
        if self.simulated:
            print('This is a simulated stage.')
            self.homed = None
        else:
            self.homed = self.get_homed_status(self, verbose=verbose)

        # Define the stage axes
        if verbose:
            print('Defining the axes')
        # Define the axes
        _axes = {}
        for axis in ['x', 'y']:
            _axes[axis] = MLS2032StageAxis(
                controller, axis, simulated, verbose
            )
        self._axes = _axes

    @property
    def axes(self) -> typing.Mapping[str, microscope.abc.StageAxis]:
        return self._axes

    def initialise(
        self, home=True, force_home=False, max_vel=None, acc=None,
        verbose=False
    ):
        """
        Initialise the XY stage.

        Parameters
        ----------
        max_vel : float
            Maximum velocity for the stage movement.
        acc : float
            Acceleration for the stage movement.
        force_home : bool
            If True, forces the stage to home even if it's already homed.
        verbose : bool
            If True, enables verbose output during operation.
        """
        if max_vel is not None or acc is not None:
            self.set_velocity_params(
                channel=None, max_vel=max_vel, acc=acc, verbose=verbose
            )
        if self.controller:
            self.controller.standard_initialize_channels(
                self, home=home, force_home=force_home, verbose=verbose
            )

    def set_velocity_params(
        self, channel=None, max_vel=None, acc=None, verbose=False
    ):
        """
        Set the velocity and acceleration parameters of the XY stage.

        Parameters
        ----------
        channel : list or None, optional
            List of channel names or numbers. If None, sets parameters for all
            channels. Defaults to None.
        max_vel : float or None, optional
            Maximum velocity. Defaults to None.
        acc : float or None, optional
            Acceleration. Defaults to None.
        verbose : bool, optional
            Whether to print additional information. Defaults to False.
        """
        if self.controller:
            self.controller.set_velocity_params(
                self, channel, max_vel, acc, verbose
            )

    def convert_to_mm(self, value, unit):
        """
        Convert a given value from specified units to millimetres (mm).

        Parameters
        ----------
        value : float
            The value to convert.
        unit : {'um', 'mm', 'cm', 'm', 'nm', 'pm'}
            The unit of the given value.

        Returns
        -------
        float
            The value converted to millimetres (mm).

        Raises
        ------
        ValueError
            If the specified unit is not supported.
        """
        # Dictionary to map units to their conversion factor to micrometers
        unit_conversion = {
            'um': 1e-3,
            'mm': 1,
            'cm': 10,
            'm': 1e3,
            'nm': 1e-6,
            'pm': 1e-9
        }
        if unit not in unit_conversion:
            raise ValueError(
                f"Unsupported unit: {unit}. Supported units are 'um', 'mm', "
                "'cm', 'm', 'nm', 'pm'."
            )
        # Perform conversion
        converted_value = value * unit_conversion[unit]

        return converted_value

    def move_by(self, delta, verbose=False):
        """Move by the specified distance."""
        if verbose:
            print('Moving by', delta)
        target_pos = (delta['x'], delta['y'])
        relative = True
        self.move(target_pos, relative)

    def move_to(self, position, verbose=False):
        """Move to the specified position."""
        if verbose:
            print('Moving to', position)
        target_pos = (position['x'], position['y'])
        relative = False
        self.move(target_pos, relative)

    def move(self, target_pos, relative, units='mm', verbose=False):
        """
        Move the XY stage to a specified end position.

        Parameters
        ----------
        target_pos : tuple
            A tuple specifying the target X and Y positions.
        relative : bool
            If True, the target position is relative to the current position.
        units : {'mm', 'cm', 'm', 'um', 'nm', 'pm'}, default 'mm'
            The unit of the target position.
        verbose : bool, default False
            If True, enables verbose output during the move operation.
        """
        target_mm_pos = self.convert_to_mm(target_pos, units)
        self.move_mm(target_mm_pos, relative, verbose)

    def move_mm(
        self, target_pos, channel=None, relative=False, max_vel=None, acc=None,
        permanent=False, verbose=False
    ):
        """
        Moves the XY stage to a specified end position.

        Parameters
        ----------
        target_pos : list or tuple
            A tuple specifying the target X and Y positions.
        channel : list or tuple or None, default None
            List of channel names or numbers. If None, moves all channels.
        relative : bool, default False
            If True, the movement is relative to the current position.
        max_vel : float or None, default None
            Maximum velocity for all channels.
        acc : float or None, default None
            Acceleration for all channels.
        permanent : bool, default False
            Whether to make velocity and acceleration changes permanent.
        verbose : bool, default False
            Whether to print additional information.
        """
        if self.controller:
            self.controller.moveTo(
                self, target_pos=target_pos, channel=channel,
                relative=relative, max_vel=max_vel, acc=acc,
                permanent=permanent, verbose=verbose
            )

    def home(self, force_home=False, verbose=False):
        """
        Home the XY stage.

        Parameters
        ----------
        force_home : bool
            If True, forces the stage to home regardless if it is homed
            already or not.
        verbose : bool
            If True, enables verbose output during the homing operation.
        """
        if verbose:
            print('Homing the stage.')
        if self.controller:
            self.controller.home_channels(
                self, channel=None, force=force_home, verbose=verbose
            )
        self.homed = True

    def get_homed_status(self, verbose=False):
        """Check if the stage is homed."""
        if verbose:
            print('Checking if the stage is homed.')

        # If this is a simulated stage
        if self.simulated:
            if verbose:
                if self.homed:
                    print('The stage is homed.')
                else:
                    print('The stage is not homed.')
            return self.homed

        # If this is note a simulated stage
        homed = []
        for idx in self.controller.channels:
            # Check if all channels are homed
            homed.append(self.channels[idx].Status.IsHomed)
        if all(homed):
            if verbose:
                print('The stage is homed.')
            return True
        else:
            if verbose:
                print('The stage is not homed.')
            return False

    def get_position(self):
        """
        Get the current position of the XY stage.

        Returns
        -------
        tuple
            The current X and Y position of the stage.
        """
        if self.controller:
            self.controller.get_position(self)

    def close(self, force, verbose):
        """
        Cleans up and releases resources of the XY stage.

        Parameters
        ----------
        force : bool
            If True, forces the stage to close regardless of its current state.
        verbose : bool
            If True, enables verbose output during cleanup.
        """
        # TODO: parameter `force` is unused
        if self.controller:
            self.controller.finish(self, verbose=verbose)

    def _do_enable(self) -> bool:
        print('Enabling the device.')
        # Before a device can moved, it first needs to establish a reference to
        # the home position. We won't be able to move unless we home it first.
        if not self.homed:
            self.home()
            self.homed = self.get_homed_status()
        return self.homed

    def may_move_on_enable(self, verbose=False) -> bool:
        if verbose:
            print('Checking if the stage may move if it is enabled.')

        may_move = not self.homed

        if verbose:
            if may_move:
                print('The stage may move when enabled.')
            else:
                print('The stage will not move when enabled.')

        return may_move

    def _do_shutdown(self) -> None:
        print('Shutting down the MLS203-2 stage.')


if __name__ == '__main__':
    print('Testing mls2032.py')

    config = {
        'name': 'XY Stage'
    }

    stage = MLS2032Stage(config, simulated=True, verbose=True)
    print(stage.stage_name)
    # Check if enabling the device will cause it to move
    print(stage.may_move_on_enable(verbose=True))
    stage.enable()
    stage.home(verbose=True)
    print(stage.get_homed_status(verbose=True))

    # Move operations
    stage.move_to({'x': 42.0, 'y': -5.1}, verbose=True)
    stage.move_by({'x': -5.3, 'y': 14.6}, verbose=True)

    # Individual axes
    x_axis = stage.axes['x']
    y_axis = stage.axes['y']
    x_axis.move_to(42.0, verbose=True)
    y_axis.move_by(-5.3, verbose=True)

    # Moves x axis to the its upper limit:
    x_axis.move_to(x_axis.limits.upper, verbose=True)

    # The same as above since the move operations are clipped to
    # the axes limits automatically.
    import math
    x_axis.move_to(math.inf, verbose=True)
    x_axis.move_by(math.inf, verbose=True)
