"""ZFM2020Stage class."""
import warnings

import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from stages.braman import BRamanZStage
from controllers.mcm3000 import MCM3000Controller


class ZFM2020Stage(BRamanZStage, MCM3000Controller):

    def __init__(self, config, controller='MCM3000'):
        """Initialise a new instance of the ZFM2020Stage class."""
        if 'port' not in config:
            raise ValueError('Configuration must have a port')
        if 'channel' not in config:
            raise ValueError('Configuration must have a channel')
        self.config = config
        self.stage_name = self.config.get('stage_name', 'ZFM2020')
        self.controller_name = self.config.get('stage_name', 'MCM3000')
        self.channel = self.config['channel']
        if self.channel not in [1, 2, 3]:
            raise ValueError(
                f'Channel must be 1, 2, or 3, currently it is: {self.channel}'
            )
        stages = tuple(
            ['ZFM2020' if i == self.channel else None for i in range(1, 4)]
        )
        reverse = tuple(
            [self.config['reverse'] if i == self.channel else False
                for i in range(1, 4)]
        )
        verbose = self.config.get('verbose', False)
        very_verbose = self.config.get('very_verbose', False)
        if 'unit' not in config:
            warnings.warn('No unit specified, defaulting to "μm"')
        unit = self.config.get('unit', 'μm')
        MCM3000Controller.__init__(
            self,
            port=self.config['port'],
            name='MCM3000',
            stages=stages,
            reverse=reverse,
            verbose=verbose,
            very_verbose=very_verbose,
            simulated=True
        )
        BRamanZStage.__init__(self, unit=unit, stage_name=self.stage_name)

    def print_info(self):
        """Print information about the stage controller."""
        print('\n---------------------')
        print('---------------------')
        print(f"Stage {self.stage_name} INFO:")
        print(f"Stage name: {self.stage_name}")
        print(f"Channel: {self.channel}")
        print(f"Port: {self.port}")
        print(f"Reverse: {self.reverse}")
        print(f"Verbose: {self.verbose}")
        print(f"Very verbose: {self.very_verbose}")
        print(f"Unit: {self.unit}")
        print(f"Position: {self.get_position(verbose=True, simulated=True)}")
        print('---------------------')
        print('---------------------\n')
        self.print_channel_info(self.channel)

    def initialize(self, force_home=False, verbose=False):
        """
        Initialise the ZFM2020 stage.

        Currently, this method indicates that the ZFM2020 stage does not
        require initialization.

        Args:
            force_home (bool): Ignored for this stage.
            verbose (bool): If True, prints the initialization message.
        """
        print('ZFM2020 Stage does not require initialization.')

    def _move_um(self, target_pos_um, relative=True, verbose=False):
        """
        Move the stage to the specified position in micrometers.

        Overrides the method to utilize the MCM3000 controller's move function
        specific to the ZFM2020's configured channel.

        Args:
            target_pos_um (float): The target position in micrometers.
            relative (bool): If True, the movement is relative to the current
            position.
            verbose (bool): If True, prints detailed movement information.
        """
        MCM3000Controller.move_um(
            self, channel=self.channel, move_um=int(target_pos_um),
            relative=relative, block=True, verbose=verbose
        )

    def _get_position_um(self, verbose=False):
        """
        Retrieve the current position of the ZFM2020 stage in micrometers.

        Utilizes the MCM3000 controller's functionality to get the current
        stage position for the configured channel.

        Args:
            verbose (bool): If True, prints detailed position information.

        Returns:
            float: The current stage position in micrometers.
        """
        return MCM3000Controller.get_position_um(
            self, channel=self.channel, verbose=verbose
        )

    def _set_retract_pos_um(
        self, retract_pos_um=None, relative=False, verbose=False
    ):
        """
        Set the retract position for the ZFM2020 stage in micrometers.

        Utilizes the MCM3000 controller's functionality to set a retract
        position for the configured channel.

        Args:
            retract_pos_um (float, optional): The retract position in
            micrometers. If None, uses current position.
            relative (bool): If True, the setting is relative to the current
            position.
            verbose (bool): If True, prints detailed information about the
            retract position setting.
        """
        MCM3000Controller.set_retract_point_um(
            self, channel=self.channel, retract_pos_um=int(retract_pos_um),
            relative=relative, verbose=verbose
        )

    def _get_initial_retract_pos_um(self):
        """
        Retrieve the initial retract position of the stage in micrometers.

        Uses the MCM3000 controller's functionality to get the retract position
        for the configured channel.

        Returns:
            float: The initial retract position in micrometers.
        """
        return MCM3000Controller.get_retract_point_um(self, self.channel)

    def set_velocity_params(self, vel_params, verbose=False):
        """
        Set the velocity parameters of the Z-stage.

        Args:
            vel_params (dict): A dictionary containing the velocity parameters
            for the stage.
            verbose (bool): If True, prints detailed information about the
            operation.
        """
        msg = 'Velocity parameters cannot be changed on stage ' + \
            f'{self.stage_name} with controller {self.controller_name}.'
        print(msg)

    def set_acceleration_params(self, acc_params, verbose=False):
        """
        Set the acceleration parameters of the Z-stage.

        Args:
            acc_params (dict): A dictionary containing the acceleration
            parameters for the stage.
            verbose (bool): If True, prints detailed information about the
            operation.
        """
        msg = 'Acceleration parameters cannot be changed on stage ' + \
            f'{self.stage_name} with controller {self.controller_name}.'
        print(msg)

    def close(self, force=False, verbose=False, simulated=False):
        """
        Close the stage controller.

        Closes the connection and optionally prints a message indicating the
        closure. Ensures that any necessary cleanup is performed.

        Args:
            force (bool): Currently unused.
            verbose (bool): If True, prints a message indicating that the stage
            controller has been closed.
        """
        MCM3000Controller.close(self, verbose=False, simulated=simulated)
        if verbose:
            print(f"{self.name} Stage closed")


if __name__ == '__main__':
    # Example of a successful initialization with valid configuration
    valid_config = {
        'port': 'COM3',
        'channel': 1,
        'stage_name': 'ZFM2020',
        'reverse': True,
        'verbose': True,
        'very_verbose': True,
        'unit': 'mm'
    }

    print('Attempting to initialize with a valid configuration...')
    try:
        controller = ZFM2020Stage(valid_config)
        controller.print_info()
        controller.close(simulated=True)
    except ValueError as e:
        print(f'Failed to initialize: {e}')

#     # Example of an initialization failure due to missing configuration keys
#     invalid_config_missing_keys = {
#         "channel": 1
#         # Missing 'port'
#     }

#     print("\nAttempting to initialize with missing configuration keys...")
#     try:
#         controller = ZFM2020StageMCM3000Controller(invalid_config_missing_keys)
#         print("Initialization successful.")
#     except ValueError as e:
#         print(f"Failed to initialize: {e}")

#     # Example of an initialization failure due to invalid channel
#     invalid_config_invalid_channel = {
#         "port": "COM4",
#         "channel": 4,  # Invalid channel number
#         "stage_name": "FaultyStage"
#     }
    
#     print("\nAttempting to initialize with an invalid channel...")
#     try:
#         controller = ZFM2020StageMCM3000Controller(invalid_config_invalid_channel)
#         print("Initialization successful.")
#     except ValueError as e:
#         print(f"Failed to initialize: {e}")

#     