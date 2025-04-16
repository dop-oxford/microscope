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
        self, controller: microscope.abc.Controller, axis: str,
        limits=[-10000, 10000], simulated=False, verbose=False
    ) -> None:
        if verbose:
            print(f"Initialising the stage's {axis} axis")
        super().__init__()
        self.controller = controller
        self.axis = axis
        self._limits = limits
        assert limits[0] < limits[1], \
            f'The minimum limit ({limits[0]}) cannot be larger or equal ' + \
            f'to the maximum limit ({limits[1]})'
        self.min_limit = limits[0]
        self.max_limit = limits[1]
        self._position = limits[0] + (limits[1] - limits[0]) / 2
        self._home_position = limits[0] + (limits[1] - limits[0]) / 2
        self.simulated = simulated

    def move_by(self, delta: float, verbose=False) -> None:
        """Move the device by the specified distance."""
        if verbose:
            print(f"Moving the stage's {self.axis} axis by {delta}")
        relative = True
        self.move(delta, relative, verbose=verbose)

    def move_to(self, pos: float, verbose=False) -> None:
        """Move the device to the specified position."""
        if verbose:
            print(f"Moving the stage's {self.axis} axis to {pos}")
        relative = False
        self.move(pos, relative, verbose=verbose)

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

    def move(self, target_pos, relative, units='mm', verbose=False):
        """Move the stage axis to a specified end position."""
        target_mm_pos = self.convert_to_mm(target_pos, units)
        self.move_mm(target_mm_pos, relative=relative, verbose=verbose)

    def move_mm(self, value, relative=False, verbose=False):
        """Move the stage axis to a specified end position."""
        # Check against the axis's limits
        if relative:
            if value + self._position > self.max_limit:
                value = self.max_limit - self._position
            if value + self._position < self.min_limit:
                value = self.min_limit + self._position
        else:
            if value > self.max_limit:
                value = self.max_limit
            if value < self.min_limit:
                value = self.min_limit
        # Update the user
        if verbose:
            if relative:
                print(f"Moving the stage's {self.axis} axis by {value} mm")
            else:
                print(f"Moving the stage's {self.axis} axis to {value} mm")
        # Move the axis
        if self.simulated:
            if relative:
                self._position += value
            else:
                self._position = value
        else:
            self.controller.moveTo(
                self, value, relative=relative, verbose=verbose
            )
            # self.controller.move_to(delta, self.name)

    @property
    def position(self) -> float:
        """Get the position of this axis."""
        if self.controller:
            if self.controller.is_busy():
                self.controller.wait_until_idle()
            return float(self.controller.get_absolute_position(self.axis))
            # return self.controller.position(self.axis)
        elif self.simulated:
            return self._position

    @property
    def limits(self) -> microscope.AxisLimits:
        """Get the limits of the position of the axis."""
        return microscope.AxisLimits(
            lower=self.min_limit, upper=self.max_limit
        )

    def get_home_position(self) -> float:
        """Get the home position of this axis."""
        return self._home_position

    def set_home_position(self, position):
        """Set the home position of this axis."""
        self._home_position = position


class MLS2032Stage(microscope.abc.Stage):
    """
    Instantiate a Thorlabs MLS203-2 stage.
    """

    def __init__(
        self, controller: microscope.abc.Controller, axes: list,
        simulated=False, verbose=False
    ):
        """Constructor method."""
        # Initialize the base class (Stage), which also handles Device
        super().__init__()
        self.controller = controller
        self.initialize()

        if verbose:
            stage_name = ''.join(axes).upper()
            print(f'Initialising the {stage_name} stage')

        self.simulated = simulated
        if self.simulated:
            print('This is a simulated stage')

        # Define the stage's axes
        _axes = {}
        for axis in axes:
            _axes[axis] = MLS2032StageAxis(
                controller, axis, simulated=simulated, verbose=verbose
            )
        self._axes = _axes

        # Check if the stage is homed
        self.homed = self.get_homed_status(verbose=verbose)

    def initialise(
        self, home=True, force_home=False, max_vel=None, acc=None,
        verbose=False
    ):
        """
        Initialise an MLS203-2 stage.

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
        Set the velocity and acceleration parameters of an MLS203-2 stage.

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
        """Move an MLS203-2 stage by the specified distance."""
        if verbose:
            print('Moving the stage by', delta)
        relative = True
        self.move(delta, relative, verbose=verbose)

    def move_to(self, position, verbose=False):
        """Move an MLS203-2 stage to the specified position."""
        if verbose:
            print('Moving the stage to', position)
        relative = False
        self.move(position, relative, verbose=verbose)

    def move(self, values, relative, units='mm', verbose=False):
        """
        Move an MLS203-2 stage to a specified end position.

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
        if verbose:
            if relative:
                print('Moving the stage by', values)
            else:
                print('Moving the stage to', values)
        values_mm = {}
        for key, value in values.items():
            values_mm[key] = self.convert_to_mm(value, units)
        self.move_mm(values_mm, relative=relative, verbose=verbose)

    def move_mm(
        self, values, channel=None, relative=False, max_vel=None, acc=None,
        permanent=False, verbose=False
    ):
        """
        Moves an MLS203-2 stage to a specified end position.

        Parameters
        ----------
        values : list or tuple
            A tuple specifying the target X, Y and Z (or a subset) positions.
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
        if self.simulated:
            for axis in self._axes.values():
                name = axis.axis
                value = values[name]
                if verbose:
                    if relative:
                        print(f"Moving the stage's {name} axis by {value} mm")
                    else:
                        print(f"Moving the stage's {name} axis to {value} mm")
                axis.move_mm(value, relative=relative, verbose=verbose)
        else:
            self.controller.moveTo(
                self, target_pos=values, channel=channel,
                relative=relative, max_vel=max_vel, acc=acc,
                permanent=permanent, verbose=verbose
            )

    @property
    def axes(self) -> typing.Mapping[str, microscope.abc.StageAxis]:
        return self._axes

    def home(self, force_home=False, verbose=False):
        """
        Home an MLS203-2 stage.

        Parameters
        ----------
        force_home : bool
            If True, forces the stage to home regardless if it is homed
            already or not.
        verbose : bool
            If True, enables verbose output during the homing operation.
        """
        if verbose:
            print('Homing the stage')
        if self.simulated:
            for axis in self._axes.values():
                axis.move_to(axis.get_home_position())
        else:
            self.controller.home_channels(
                self, channel=None, force=force_home, verbose=verbose
            )
        self.homed = self.get_homed_status(verbose=False)

    def get_homed_status(self, verbose=False):
        """Check if an MLS203-2 stage is homed."""
        if verbose:
            print('Checking if the stage is homed')

        # If this is a simulated stage
        homed = []
        if self.simulated:
            for axis in self._axes.values():
                homed.append(axis.position == axis.get_home_position())
            if all(homed):
                if verbose:
                    print('The stage is homed')
                return True
            else:
                if verbose:
                    print('The stage is not homed')
                return False

        # If this is not a simulated stage
        homed = []
        for idx in self.controller.channels:
            # Check if all channels are homed
            homed.append(self.channels[idx].Status.IsHomed)
        if all(homed):
            if verbose:
                print('The stage is homed')
            return True
        else:
            if verbose:
                print('The stage is not homed')
            return False

    def get_position(self, verbose=False):
        """
        Get the current position of an MLS203-2 stage.

        Returns
        -------
        tuple
            The current position of the stage.
        """
        if verbose:
            print('Getting the current position of the stage')

        positions = []
        if self.simulated:
            for axis in self._axes.values():
                positions.append(axis.position)
            return positions
        else:
            self.controller.get_position(self)

    def close(self, force, verbose):
        """
        Cleans up and releases resources of an MLS203-2 stage.

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

    def _do_enable(self, verbose=False) -> bool:
        if verbose:
            print('Enabling the device')
        # Before a device can moved, it first needs to establish a reference to
        # the home position. We won't be able to move unless we home it first.
        if not self.homed:
            self.home()
            self.homed = self.get_homed_status()
        return self.homed

    def may_move_on_enable(self, verbose=False) -> bool:
        if verbose:
            print('Checking if the stage may move if it is enabled')
        return not self.homed

    def _do_shutdown(self) -> None:
        print('Shutting down the MLS203-2 stage')


if __name__ == '__main__':
    print('Testing mls2032.py')

    controller = None
    axes = ['x', 'y']
    stage = MLS2032Stage(controller, axes, simulated=True, verbose=True)

    # Check if enabling the device will cause it to move
    print(stage.may_move_on_enable(verbose=True))
    stage.enable()
    stage.home(verbose=True)
    print(stage.get_homed_status(verbose=True))
    print('')

    # Move operations
    stage.move_to({'x': 42.0, 'y': -5.1}, verbose=True)
    print(stage.get_position(verbose=True))
    print('')
    stage.move_by({'x': -5.3, 'y': 14.6}, verbose=True)
    print(stage.get_position(verbose=True))
    print('')

    # Home the stage
    print(stage.get_position(verbose=True))
    stage.get_homed_status(verbose=True)
    stage.home(verbose=True)
    print(stage.get_position(verbose=True))
    stage.get_homed_status(verbose=True)
    print('')

    # Individual axes
    x_axis = stage.axes['x']
    y_axis = stage.axes['y']
    x_axis.move_to(42.0, verbose=True)
    y_axis.move_by(-5.3, verbose=True)
    y_axis.move_by(1.2, verbose=True)
    print(stage.get_position(verbose=True))
    print('')

    # Move the x-axis to its upper limit
    x_axis.move_to(x_axis.limits.upper, verbose=True)
    print(stage.get_position(verbose=True))
    print('')

    # Move the x-axis beyond its upper limit
    # (this is the same as above because the move operations are clipped to
    # the axes' limits automatically)
    import math
    x_axis.move_to(math.inf, verbose=True)
    print(stage.get_position(verbose=True))
    y_axis.move_by(math.inf, verbose=True)
    print(stage.get_position(verbose=True))
    print('')
