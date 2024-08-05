"""
Implementation of a simulated galvanometer module.

This file is part of Microscope.

Microscope is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Microscope is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Microscope.  If not, see <http://www.gnu.org/licenses/>.
"""
# Standard library
import logging
# Custom module
import microscope
import typing

import microscope.abc

# Set up configuration for the logger
logging.basicConfig(
    filename='galvo.log',
    level=logging.INFO,
    filemode='w',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
_logger = logging.getLogger(__name__)

class _GalvoAxis(microscope.abc.StageAxis):
    def __init__(self, dev_conn: _ZaberDeviceConnection, axis: int) -> None:
        super().__init__()
        self._dev_conn = dev_conn
        self._axis = axis
    def move_by(self, delta: float) -> None:
        """Move axis by given amount."""
        pass
    
    def move_to(self, pos: float) -> None:
        """Move axis to specified position."""
        pass

    def position(self) -> float:
        """Current axis position."""
        raise NotImplementedError()

    def limits(self) -> microscope.AxisLimits:
        """Upper and lower limits values for position."""
        return self._limits

class _GalvoScanner(microscope.abc.Stage):
    def __init__(self, num_axes=2, linear_conversion=None, angle_limits=None, axes_names=['X', 'Y'], verbose=False):
        """
        Initializes a GalvoScanner object with specified parameters.

        Args:
            num_axes (int, optional): The number of axes the scanner operates. Defaults to 2.
            linear_conversion (float, list of float, optional): A single conversion factor or a list of conversion factors from angle to linear motion for each axis. If None, defaults to 1 for each axis.
            angle_limits (list of list/tuple, optional): A list of lists or tuples specifying min and max angles for each axis. Defaults to (-10, 10) for each axis if None.
            axes_names (list of str, optional): The names of the axes. Defaults to ['X', 'Y'].
            verbose (bool, optional): If set to True, the scanner will print actions and statuses. Defaults to False.
        """
        super().__init__()
        if len(axes_names) < num_axes:
            raise ValueError("Number of axis names must be at least equal to num_axes")
        self.num_axes = num_axes

        self._axes = {axes_names[i]: _GalvoAxis(axes_names[i]) for i in range(num_axes)}
        
        # Handle linear_conversion input
        if isinstance(linear_conversion, (int, float)):
            self.linear_conversion = {axis: linear_conversion for axis in self._axes}
        elif isinstance(linear_conversion, list):
            if len(linear_conversion) != num_axes:
                raise ValueError("Length of linear_conversion must match num_axes")
            self.linear_conversion = {axis: conv for axis, conv in zip(self._axes, linear_conversion)}
        else:
            self.linear_conversion = {axis: 1 for axis in self._axes}  # Default value
        
        # Handle angle_limits input
        
        self.verbose = verbose
        self._target_angle = {axis: None for axis in self._axes}
        
        # Initialize positions - Implementation needed based on actual mechanism to get positions
        self.position_ang = self.get_position_ang(verbose=True)
        self.position_lin = {axis: self.angle_to_linear(axis, self.position_ang[axis]) for axis in self._axes}

    def _do_shutdown(self) -> None:
        pass

    def _do_enable(self) -> None:
        self.position_ang = self.get_position_ang(verbose=True)
        self.position_lin = {axis: self.angle_to_linear(axis, self.position_ang[axis]) for axis in self._axes}

    @property
    def axes(self) -> typing.Mapping[str, microscope.abc.StageAxis]:
        return self._axes

    @abstractmethod
    def _set_angle_ax(self, angle, axis=0):
        """Set the angle of a specified axis."""
        pass

    @abstractmethod
    def _get_angle_ax(self, axis=0):
        """Get the current angle of a specified axis."""
        pass

    def shutdown(self) -> None:
        self._do_shutdown()
    
    def _do_shutdown(self):
        """Nothing to do"""
        pass
    
    def _set_angles(self, angles):
        """Sets the angles for all the axes

        Args:
            angles (str, int, list of str, or list of int): The angles to set the axes to. 
                Can be a single name or index, or a list of names or indices, depending on the number of axes.

        Raises:
            ValueError: If the number of angles does not match the number of axes.
        """
        if not isinstance(angle, (list, tuple)):
            angle = [angle]
        if len(angles) != self.num_axes:
            raise ValueError(f"Axes {self._axes} cannot be set with angles {angles}(expected {self.num_axes} angles)")
        for axis, angle in angles.items():
            self._set_angle_ax(angle, axis)
    
      
    def _get_angles(self):
        """Gets the angles for all the axes

        Returns:
            dict: A dictionary with the current angular positions for all the axes.
        """
        return {axis: self._get_angle_ax(axis) for axis in self._axes}
    
    
    def validate_angles(self, angles, axis=None):
        """
        Validates the specified angle or angles against the allowed range for the corresponding axis or axes.
        
        This method can handle a single angle with its axis or a dictionary mapping axes to their angles.
        For a single angle, the axis must be provided either as a name (str) or an index (int).
        For multiple angles, angles must be a dictionary where each key-value pair corresponds to an axis and its angle.

        Args:
            angles (float or dict): If a single angle is provided, it's a float. If multiple angles are provided, it's a dictionary mapping each axis (str or int) to its angle (float).
            axis (str or int, optional): The axis for a single angle input. Required if `angles` is a single float. Ignored if `angles` is a dictionary.

        Returns:
            float or dict: The validated angle if a single angle was provided, or a dictionary of validated angles if a dictionary was provided.

        Raises:
            ValueError: If any angle is out of the allowed range for its axis, or if `axis` is not provided for a single angle.
            TypeError: If the input format of `angles` or `axis` is incorrect.
        """
        if isinstance(angles, (float, int)):  # Single angle provided
            if axis is None:
                raise ValueError("Axis must be provided for a single angle validation.")
            if isinstance(axis, int):
                if axis < 0 or axis >= self.num_axes:
                    raise ValueError(f"Axis index '{axis}' is out of range. Must be between 0 and {self.num_axes - 1}.")
                axis_name = self._axes[axis]  # Convert index to name if necessary
            else:
                axis_name = axis
                self.validate_axes(axis)  # Validates the single axis name
            if not self.angle_limits[axis_name][0] <= angles <= self.angle_limits[axis_name][1]:
                raise ValueError(f"Angle {angles} out of allowed range for axis {axis_name}")
            return angles
        elif isinstance(angles, dict):  # Multiple angles provided
            validated_angles = {}
            for ax, ang in angles.items():
                if isinstance(ax, int):
                    if ax < 0 or ax >= self.num_axes:
                        raise ValueError(f"Axis index '{ax}' is out of range. Must be between 0 and {self.num_axes - 1}.")
                    ax = self._axes[ax]  # Convert index to name
                self.validate_axes(ax)  # Validates each axis name
                if not self.angle_limits[ax][0] <= ang <= self.angle_limits[ax][1]:
                    raise ValueError(f"Angle {ang} out of allowed range for axis {ax}")
                validated_angles[ax] = ang
            return validated_angles
        else:
            raise TypeError("Angles must be a single float/int (with `axis` provided) or a dictionary of axis-angle pairs.")

        
    def validate_axes(self, axes):
        """
        Validates that the specified axis or axes are valid, unique, and within the allowed range.
        
        This method can handle a single axis as either a string (name) or an integer (index), 
        or a list of axes as strings or integers. If a single axis is provided, it checks if 
        the axis is valid. If a list of axes is provided, it additionally checks for uniqueness 
        among them and ensures all indices are within the allowed range based on `self.num_axes`.

        Args:
            axes (str, int, list of str, or list of int): The axis or axes to validate. 
                Can be a single name or index, or a list of names or indices.

        Returns:
            str, int, or list of str/int: The validated axis or axes. The format matches the input.

        Raises:
            ValueError: If any provided axis is invalid, if duplicate axes are found, or if any 
                axis index is out of range.
            TypeError: If the input format is incorrect.
        """
        if isinstance(axes, (str, int)):
            # Single axis provided
            if isinstance(axes, int):
                if axes < 0 or axes >= self.num_axes:
                    raise ValueError(f"Axis index '{axes}' is out of range. Must be between 0 and {self.num_axes - 1}.")
            elif axes not in self._axes:
                raise ValueError(f"Invalid axis name '{axes}', valid axes are {self._axes}")
            return axes
        elif isinstance(axes, list):
            # List of axes provided
            if all(isinstance(axis, int) for axis in axes):
                if any(axis < 0 or axis >= self.num_axes for axis in axes):
                    raise ValueError("Axis index out of range.")
            elif not all(isinstance(axis, (str, int)) for axis in axes):
                raise TypeError("All axes must be of the same type, either int or str.")
            if len(set(axes)) != len(axes):
                raise ValueError("Duplicate axes found. Each axis must be unique.")
            for axis in axes:
                if isinstance(axis, str) and axis not in self._axes:
                    raise ValueError(f"Invalid axis name '{axis}', valid axes are {self._axes}")
            return axes
        else:
            # Invalid input type
            raise TypeError("Axes must be either a single axis name (str) / index (int) or a list of axis names / indices (list of str/int).")

    
    
    def get_position(self, axes=None, verbose=True):
        """Retrieves the current angular positions for the specified axes.
        
        Args:
            axes (list of str, optional): The axes to retrieve positions for. If None, retrieves for all configured axes.
            verbose (bool, optional): If True, prints the angular positions to the console.
        
        Returns:
            dict: A dictionary with the current angular positions for the specified axes.
        """
        # If no specific axes are provided, use all configured axes.
        if axes is None:
            axes = self._axes
        else:
            # Ensure axes is a list for consistent processing below.
            axes = [axes] if isinstance(axes, (str, int)) else axes
        
        # Initialize a dictionary to hold the positions.
        positions = {}
        
        # Validate and retrieve position for each specified axis.
        for axis in axes:
            self.validate_axes(axis)  # Ensure the axis is valid. Note: validate_axis might need to handle int indices too.
            positions[axis] = self.get_angle_ax(axis)  # Retrieve and store the position for the axis.
        
        # Optionally print the positions if verbose is True.
        if verbose:
            print(f"Angular position(s) for {axes}: {positions} degrees")
        
        # Update the internal linear position.
        self.position_lin = {axis: self.angle_to_linear(axis, self.position_ang[axis]) for axis in self._axes}
        
        return positions

    
    def get_position_lin(self, axes=None, verbose = True):
        """Retrieves the current linear positions for the specified axes.
        
        Args:
            axes (list of str, optional): The axes to retrieve positions for. If None, retrieves for all configured axes.
            verbose (bool, optional): If True, prints the angular positions to the console.
        
        Returns:
            dict: A dictionary with the current linear positions for the specified axes.
        """
        if axes is None:
            axes = self._axes
        self.get_position_ang(axes, verbose=False)
        if verbose:
            print(f"Linear position for {axes}: {self.position_lin[axes]}")
        return self.position_lin[axes]
    
        
    def _motion_finished(self, axis=0, tolerance=0.1):
        """Check if the motion for the specified axis is finished.

        Args:
            axis (int, optional): The axis to check. Defaults to 0.
            tolerance (float, optional): The tolerance within which the target must be met, in degrees. Defaults to 0.1.

        Returns:
            bool: True if the motion is finished, False otherwise
        """
        current_angle = self.get_angle_ax(axis)
        return abs(current_angle - self._target_angle[axis]) < tolerance
    
 

    def move_to_position(self, axis, angle, relative=False, timeout_s=5000, tolerance=0.1):
        """Moves one or more axes to the specified angle(s).
        
        Args:
            axis (str or list of str): A single axis as a string or a list of axes.
            angle (float or list of float): A single angle value or a list of angle values corresponding to the axis/axes.
            relative (bool, optional): If True, moves the axis/axes to a position relative to the current position.
            timeout_s (int, optional): Timeout in seconds for the movement.
            tolerance (float, optional): The tolerance within which the target must be met, in degrees.
        
        Raises:
            ValueError: If the lengths of axis and angle lists do not match.
            TimeoutError: If the movement cannot be completed within the specified timeout.
        """
        # Ensure axis and angle are lists for consistent processing
        if not isinstance(axis, (list, tuple)):
            axis = [axis]
        if not isinstance(angle, (list, tuple)):
            angle = [angle]

        # Validate that the number of axes and angles provided match
        if len(axis) != len(angle):
            raise ValueError("Axis and angle parameters must have the same length.")
        
        for ax, ang in zip(axis, angle):
            self.validate_axis(ax)
            target_angle = ang + self.position_ang[ax] if relative else ang
            self._target_angle[ax] = self.validate_angle(target_angle, ax)

            if self.verbose:
                print(f"Setting angle of axis {ax} to {target_angle} degrees")
            self.set_angle(ax, target_angle)  # Assume set_angle has been adjusted to immediately set the angle
        
        # Check motion completion for all axes
        start_time = time.time()
        while True:
            if all(self._motion_finished(ax, tolerance) for ax in axis):
                break  # Exit the loop if all motions are finished
            if (time.time() - start_time) > timeout_s:
                # Collect current angles for detailed timeout error message
                current_angles = {ax: self.get_angle_ax(ax) for ax in axis}
                raise TimeoutError(f"Timeout reached, motion not finished after {timeout_s} s. "
                                f"Current positions: {current_angles}, target positions: {self._target_angle}.")
            time.sleep(0.01)  # Small delay to prevent spamming the _motion_finished function

        # Update the stored positions after movement
        for ax in axis:
            self.position_ang[ax] = self.get_angle_ax(ax)

        

    def angle_to_linear(self, axis, angle):
        """Converts an angle to linear motion for a specified axis.
        
        Args:
            axis (str): The name of the axis.
            angle (float): The angle to convert.
        
        Returns:
            float: The equivalent linear motion.
        """
        return angle * self.linear_conversion[axis]
class GVS201_Controller(_GalvoScanner):
    def __init__(self, linear_conversion=1, voltage_to_deg_set=0.8, axis_name='X', verbose=False):
        """
        Initializes the GVS201_Controller with specific parameters and validation checks.

        Args:
            linear_conversion (float): Conversion factor from angle to linear motion for the axis.
            voltage_to_deg_set (float): Conversion factor from input voltage to degrees. Must be one of the accepted values.
            axis_name (str): Name of the controlled axis. Defaults to 'X'.
            verbose (bool): If True, enables verbose output.

        Raises:
            ValueError: If the provided voltage_to_deg_set is not in the list of accepted values.
        """
        super().__init__(num_axes=1, linear_conversion=linear_conversion, angle_limits=[(-12.5,+12.5)], axes_names=axis_name, verbose=verbose)
        accepted_voltage_to_deg_set = [0.5, 0.8, 1] # Accepted values for GVS201 (see manual)
        if voltage_to_deg_set not in accepted_voltage_to_deg_set:
            raise ValueError(f"Accepted values for voltage_to_deg_set are {accepted_voltage_to_deg_set}")
        self._voltage_to_deg_set = voltage_to_deg_set
        self._voltage_to_deg_get = 0.5 # Always 0.5 v/deg for GVS201 (see manual)
        self._input_voltage_limits = (-10,10) # Input voltage range of GVS201 (see manual)
        
    @abstractmethod
    def set_command_input_voltage(self, voltage):
        """
        Abstract method to set the command input voltage.

        Implementations should set the specified voltage as the command input for the GVS201.

        Args:
            voltage (float): The voltage to set as the command input.
        """
        pass
    
    @abstractmethod
    def get_diagnosis_connector_pin_voltage(pin):
        """
        Abstract method to get the voltage from a specific diagnosis connector pin.

        Implementations should return the voltage read from the specified pin of the diagnosis connector.

        Args:
            pin (int): The diagnosis connector pin number from which to read the voltage.

        Returns:
            float: The voltage read from the specified diagnosis connector pin.
        """
        pass
        
    def angle_to_voltage_set(self, angle):
        """
        Converts an angle to the corresponding set voltage according to the conversion factor.

        Args:
            angle (float): The angle in degrees to be converted.

        Returns:
            float: The corresponding voltage to set for the specified angle.
        """
        return angle / self._voltage_to_deg_set
    
    def angle_to_voltage_read(self, angle):
        """
        Converts an angle to the corresponding read voltage according to the conversion factor.

        Args:
            angle (float): The angle in degrees to be converted.

        Returns:
            float: The corresponding voltage read for the specified angle.
        """
        return angle / self._voltage_to_deg_get
    
    def validate_voltage(self, voltage):
        """
        Validates if the specified voltage is within the allowed input voltage range for the GVS201.

        Args:
            voltage (float): The voltage to validate.

        Raises:
            ValueError: If the voltage is outside of the allowed range.
        """
        if not self._input_voltage_limits[0] <= voltage <= self._input_voltage_limits[1]:
            raise ValueError(f"Voltage {voltage} out of allowed range for GVS201")
    
    def set_angle(self, angle, axis=0):
        """
        Sets the angle for the specified axis by converting the angle to voltage and validating it.

        Args:
            angle (float): The target angle to set.
            axis (int, optional): The axis to which the angle is set. Defaults to 0 as GVS201 is a single-axis controller, so it actually ignores whatver is written.
        """
        voltage = self.angle_to_voltage_set(angle)
        self.validate_voltage(voltage)
        self.set_command_input_voltage(self.angle_to_voltage_set(angle))
        
    def get_angle(self, axis=0):
        """
        Gets the current angle of the specified axis.

        Args:
            axis (int, optional): The axis from which to get the angle. Defaults to 0 as GVS201 is a single-axis controller.

        Returns:
            float: The current angle of the specified axis in degrees.
        """
        return super().get_angle(axis)
    
    def get_scanner_position_deg(self):
        """
        Gets the current position of the scanner in degrees.

        Returns:
            float: The current position of the scanner in degrees.
        """
        return self.get_diagnosis_connector_pin_voltage(pin=1)*self._voltage_to_deg_get

    def get_internal_command_signal_deg(self):
        """
        Gets the internal command signal in degrees.

        Returns:
            float: The internal command signal in degrees.
        """
        return self.get_diagnosis_connector_pin_voltage(pin=2)*self._voltage_to_deg_get

    def get_position_error_deg(self):
        """
        Returns the position error in degrees.

        Returns:
            float: The position error in degrees.
        """
        return self.get_diagnosis_connector_pin_voltage(pin=3)*self._voltage_to_deg_get/5

    def get_motor_drive_current(self):
        """
        Returns the motor drive current in Amperes.

        Returns:
            float: The motor drive current in A.
        """
        return self.get_diagnosis_connector_pin_voltage(pin=4)/2
    
    def get_motor_coil_voltage(self):
        """
        Returns the motor coil voltage in Volts.

        Returns:
            float: The motor coil voltage in V.
        """
        return self.get_diagnosis_connector_pin_voltage(pin=5)*2
    
    def _motion_finished(self, axis=0, tolerance=0.1):
        """
        Check if the motion for the specified axis is finished.
        
        :param axis: The axis to check (defaults to 0 in this case)
        :param tolerance: The tolerance within which the target must be met, in degrees
        :return: True if the motion is finished, False otherwise
        """
        return self.get_position_error_deg() < tolerance
    



if __name__ == '__main__':
    print('Hello, World!')

    # Instantiate a real galvo
    actual_galvo = Galvo()
    # Shutdown the real galvo
    actual_galvo.shutdown()

    # Instantiate a simulated galvo
    simulated_galvo = SimulatedGalvo()
    print(simulated_galvo.get_current())
    simulated_galvo.shutdown()
    print(simulated_galvo.get_current())
