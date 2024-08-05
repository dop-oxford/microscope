"""BRamanZStage Abstract Base Class."""
from abc import ABC, abstractmethod

# Dictionary to map units to their conversion factor to micrometers
unit_conversion_um = {
    'um': 1,
    'mm': 1e3,
    'cm': 1e4,
    'm': 1e6,
    'nm': 1e-3,
    'pm': 1e-6
}


class BRamanZStage(ABC):
    """
    An abstract base class for Z-stage controllers.

    Attributes:
        unit (str): The unit of measurement for stage positions (default is
        'um').
        retract_pos_um (float): The retract position of the stage in
        micrometers.
        stage_name (str): A human-readable name for the stage.
    """

    def __init__(self, unit='um', stage_name='Z Stage', simulated=False):
        """
        Initialise a ZStageController object.

        Args:
            unit (str): The unit of measurement for stage positions. Supported
            units are 'um', 'mm', 'cm', 'm', 'nm', 'pm'.
            stage_name (str): A human-readable name for the stage.
        """
        self.unit = self.validate_unit(unit)
        self.retract_pos_um = self._get_initial_retract_pos_um()
        self.stage_name = stage_name

    @staticmethod
    def validate_unit(unit):
        """
        Validate the provided unit of measurement.

        Args:
            unit (str): The unit of measurement to validate.

        Returns:
            str: The validated unit of measurement.

        Raises:
            ValueError: If the unit is not supported.
        """
        if not isinstance(unit, str):
            msg = f'Unit must be a single string, currently {type(unit)}'
            raise TypeError(msg)
        if unit not in unit_conversion_um:
            msg = f'Unsupported unit: {unit}. ' + \
                f'Supported units are {unit_conversion_um.keys()}.'
            raise ValueError(msg)
        return unit

    @staticmethod
    def get_conversion_factor(unit):
        """
        Return the conversion factor to convert a given unit to micrometers.

        Args:
            unit (str): The unit to convert to micrometers. Supported units are
            'um', 'mm', 'cm', 'm', 'nm', 'pm'.

        Returns:
            float: The conversion factor to convert the given unit to
            micrometers.

        Raises:
            ValueError: If the specified unit is not supported.
        """
        return unit_conversion_um[BRamanZStage.validate_unit(unit)]

    @staticmethod
    def unit_to_um(value, unit):
        """
        Convert a given value from specified units to micrometers (um).

        Args:
            value (float): The value to convert.
            unit (str): The unit of the given value. Supported units are 'um',
            'mm', 'cm', 'm', 'nm', 'pm'.

        Returns:
            float: The value converted to micrometers (um).

        Raises:
            ValueError: If the specified unit is not supported.
        """
        return value * unit_conversion_um[BRamanZStage.validate_unit(unit)]

    @staticmethod
    def um_to_unit(value_um, unit):
        """
        Convert a given value from micrometers (um) to specified units.

        Args:
            value_um (float): The value to convert in micrometers.
            unit (str): The unit to convert the value to. Supported units are
            'um', 'mm', 'cm', 'm', 'nm', 'pm'.

        Returns:
            float: The value converted to the specified unit.

        Raises:
            ValueError: If the specified unit is not supported.
        """
        return value_um / unit_conversion_um[BRamanZStage.validate_unit(unit)]

    @abstractmethod
    def print_info(self):
        """Print information about the stage controller."""
        pass

    @abstractmethod
    def initialize(self, force_home=False, verbose=False):
        """
        Initialise the Z-stage controller.

        This method should prepare the stage for operation, potentially homing
        the stage if specified.

        Args:
            force_home (bool): If True, forces the stage to home its position
            upon initialization.
            verbose (bool): If True, enables verbose output during the
            operation.
        """
        pass

    @abstractmethod
    def _move_um(self, target_pos_um, relative=False, verbose=False):
        """
        Move the stage to a specified position in micrometers.

        This method should be implemented to move the stage to a target
        position. The movement can be absolute or relative to the current
        position.

        Args:
            target_pos_um (float): The target position in micrometers.
            relative (bool): If True, the movement is relative to the current
            position; otherwise, it is absolute.
            verbose (bool): If True, enables verbose output during the
            movement.
        """
        pass

    @abstractmethod
    def _get_position_um(self, verbose=False):
        """
        Retrieve the current position of the Z-stage in micrometers.

        This method should return the current position of the stage. If verbose
        is True, it may also print this information.

        Args:
            verbose (bool): If True, enables verbose output.

        Returns:
            float: The current position of the stage in micrometers.
        """
        pass

    @abstractmethod
    def _set_retract_pos_um(
        self, retract_pos_um=None, relative=False, verbose=False
    ):
        """
        Set the retract position of the Z-stage in micrometers.

        This method should be implemented to set a specific position as the
        retract position. This position can be used to quickly retract the
        stage to a safe or predefined position.

        Args:
            retract_pos_um (float, optional): The target retract position in
            micrometers. If not specified, uses the current position.
            relative (bool): If True, the target position is relative to the
            current position.
            verbose (bool): If True, enables verbose output during the
            operation.
        """
        pass

    @abstractmethod
    def _get_initial_retract_pos_um(self):
        """
        Retrieve the initial retract position of the Z-stage in micrometers.

        This method should return the initial or default retract position of
        the stage. It is used during the initialization to set a starting
        retract position.

        Returns:
            float: The initial retract position of the stage in micrometers.

        """
        pass

    @abstractmethod
    def close(self, force, verbose):
        """
        Close the Z-stage controller.

        This method should be implemented by subclasses to close connections,
        release resources, or perform other cleanup actions specific to the
        controller.
        """
        pass

    @abstractmethod
    def set_velocity_params(self, vel_params, verbose=False):
        """
        Set the velocity parameters of the Z-stage.

        Args:
            vel_params (dict): A dictionary containing the velocity parameters
            for the stage.
            verbose (bool): If True, prints detailed information about the
            operation.
        """
        pass

    @abstractmethod
    def set_acceleration_params(self, acc_params, verbose=False):
        """
        Set the acceleration parameters of the Z-stage.

        Args:
            acc_params (dict): A dictionary containing the acceleration
            parameters for the stage.
            verbose (bool): If True, prints detailed information about the
            operation.
        """
        pass

    def set_unit(self, unit):
        """
        Set the unit of measurement for the stage positions.

        Validates and sets the unit of measurement for the stage positions to
        the specified unit. Supported units are defined in the class's
        `unit_conversion_um` dictionary.

        Args:
            unit (str): The unit of measurement to set.

        Raises:
            ValueError: If the specified unit is not supported.
        """
        self.unit = self.validate_unit(unit)

    def move(self, target_pos, relative=False, unit=None, verbose=False):
        """
        Move the stage to the specified position.

        Converts the target position from the specified unit to micrometers and
        moves the stage to this position. The movement can be absolute or
        relative to the current position.

        Args:
            target_pos (int or float): The target position in the specified or
            default unit.
            relative (bool): If True, the movement is relative to the current
            position.
            unit (str, optional): The unit of the target position. If not
            specified, uses the default unit.
            verbose (bool): If True, prints detailed information about the
            movement.

        Raises:
            ValueError: If `target_pos` is not an integer or float.
        """
        if not isinstance(target_pos, (int, float)):
            msg = 'Retract position must be a single int or float value'
            raise ValueError(msg)
        if unit is None:
            unit = self.unit
        unit = self.validate_unit(unit)
        target_pos_um = self.unit_to_um(target_pos, unit)
        self._move_um(target_pos_um, relative, verbose)
        if verbose:
            print(f'Stage Z moved to position {target_pos_um} {unit}')

    def set_retract(
        self, retract_pos=None, relative=False, unit=None, verbose=False
    ):
        """
        Set the retract position of the stage.

        Defines a retract position for the stage, which can be used to quickly
        retract the stage to a predefined position. The retract position can be
        specified in any supported unit and converted to micrometers.

        Args:
            retract_pos (int, float, optional): The retract position in the
            specified or default unit.
            relative (bool): If True, the retract position is relative to the
            current position.
            unit (str, optional): The unit of the retract position. If not
            specified, uses the default unit.
            verbose (bool): If True, prints detailed information about the
            operation.

        Raises:
            ValueError: If `retract_pos` is specified and is not an integer or
            float.
        """
        if unit is None:
            unit = self.unit
        unit = self.validate_unit(unit)
        if retract_pos is None:
            retract_pos = self.get_position(unit=unit)
        if not isinstance(retract_pos, (int, float)):
            msg = 'Retract position must be a single int or float value'
            raise ValueError(msg)
        retract_pos_um = self.unit_to_um(retract_pos, unit)
        self._set_retract_pos_um(retract_pos_um, relative)
        self.retract_pos_um = retract_pos_um
        if verbose:
            print(f'Retract point set to {retract_pos_um} {unit}')

    def retract(self, verbose=False):
        """
        Move the stage to the retract position.

        Moves the stage to the previously set retract position. If no retract
        position is set, raises an exception.

        Args:
            verbose (bool): If True, prints detailed information about the
            movement.

        Raises:
            Exception: If retract position is not set.
        """
        if self.retract_pos_um is None:
            raise Exception('Retract point not set')
        else:
            if verbose:
                msg = f'Moving to retract position {self.retract_pos_um} um...'
                print(msg)
            self._move_um(self.retract_pos_um, relative=False)
            if verbose:
                print('Stage RETRACTED')

    def get_position(self, unit=None, verbose=False, simulated=False):
        """
        Retrieve the current position of the Z-stage.

        Returns the current position of the stage in the specified or default
        unit.

        Args:
            unit (str, optional): The unit in which to return the position. If
            not specified, uses the default unit.
            verbose (bool): If True, prints detailed information about the
            current position.

        Returns:
            float: The current position of the stage in the specified or
            default unit.
        """
        if simulated:
            return 'The position is simulated'
        if unit is None:
            unit = self.unit
        unit = self.validate_unit(unit)
        pos = self._get_position_um(verbose=False, simulated=simulated)
        if verbose:
            msg = f'Current Z Stage ({self.stage_name}) position: {pos} {unit}'
            print(msg)
        return self.um_to_unit(pos, unit)
