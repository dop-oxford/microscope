"""ZFM2020Stage Class."""

import warnings

import sys
import os

from microscope.stages.generic import BRamanZStage
import microscope


class ZFM2020Stage(BRamanZStage):
    # NOTE(ADW): This class is intended to simply be device specific config for the BramanZstage,
    # we can keep alvaros code with the move um etc. but they need to call the abstract methods of the stage
    # class and not be implemented directly.

    # TODO: all the getter and setter methods should be implemented using the settings system from mscope.

    # TODO: The global kwargs verbose, very_verbose, and simulated need to be stripped, simulated should only
    # be a kwarg to __init__, verbose and very_verbose should be converted to log levels.
    def __init__(self, *args, **kwargs):
        # TODO: Currently I am passing in nonsense to the conn argument of the super class,
        # here we need a way to define what controller instance we are using inside the device_server call.
        super().__init__("Test_controller", **kwargs)

        if len(args) == 0:
            # NOTE(ADW): An approach that might work here is the init by kwargs method here if we do not pass a config but this may turn out to be unnecessary.
            self._init_kwargs(**kwargs)
        elif len(args) == 1:
            config = args[0]
            if "port" not in config:
                raise ValueError("Configuration must have a port")
            if "channel" not in config:
                raise ValueError("Configuration must have a channel")
            self.port = config["port"]
            self.reverse = config.get("reverse", False)
            self.config = config
            self.verbose = config.get("verbose", False)
            self.very_verbose = config.get("very_verbose", False)
            self.unit = config.get("unit", "μm")
            self.stage_name = self.config.get("stage_name", "ZFM2020")
            self.controller_name = self.config.get("stage_name", "MCM3000")
            self.channel = self.config["channel"]
            if self.channel not in [1, 2, 3]:
                raise ValueError(
                    f"Channel must be 1, 2, or 3, currently it is: {self.channel}"
                )
            stages = tuple(
                ["ZFM2020" if i == self.channel else None for i in range(1, 4)]
            )
            reverse = tuple(
                [
                    self.config["reverse"] if i == self.channel else False
                    for i in range(1, 4)
                ]
            )
            verbose = self.config.get("verbose", False)
            very_verbose = self.config.get("very_verbose", False)
            if "unit" not in config:
                warnings.warn('No unit specified, defaulting to "μm"')
            unit = self.config.get("unit", "μm")

            self.initialize()

    def _init_kwargs(self, **kwargs):
        if "port" not in kwargs:
            raise ValueError("Configuration must have a port")
        if "channel" not in kwargs:
            raise ValueError("Configuration must have a channel")
        self.port = kwargs["port"]
        self.channel = kwargs["channel"]
        if self.channel not in [1, 2, 3]:
            raise ValueError(
                f"Channel must be 1, 2, or 3, currently it is: {self.channel}"
            )
        self.stage_name = kwargs.get("stage_name", "ZFM2020")
        if "limits" in kwargs:
            self._limts = self._set_limits(kwargs["limits"])
        else:
            self._limits = self._set_limits([0, 1e3])

    # TODO: This can be replicated across other stage classes.
    def _set_limits(self, limits):
        if len(limits) != 2:
            raise ValueError("Limits must be a list of two values")
        if limits[0] >= limits[1]:
            raise ValueError("Lower limit must be less than upper limit")
        self._limits = microscope.AxisLimits(lower=limits[0], upper=limits[1])

    def limits(self):
        return self._limits

    def print_info(self):
        """
        Prints information about the stage controller.
        """
        print("\n---------------------")
        print("---------------------")
        print(f"Stage {self.stage_name} INFO:")
        print(f"Stage name: {self.stage_name}")
        print(f"Channel: {self.channel}")
        print(f"Port: {self.port}")
        print(f"Reverse: {self.reverse}")
        print(f"Verbose: {self.verbose}")
        print(f"Very verbose: {self.very_verbose}")
        print(f"Unit: {self.unit}")
        print(f"Position: {self.position()}")
        print("---------------------")
        print("---------------------\n")

    def initialize(self, force_home=False, verbose=False):
        """
        Initializes the ZFM2020 stage.

        Currently, this method indicates that the ZFM2020 stage does not require initialization.

        Args:
            force_home (bool): Ignored for this stage.
            verbose (bool): If True, prints the initialization message.
        """
        # TODO: We need to add_setting for each setting of the device. with args:
        # name,
        # dtype,
        # get_func,
        # set_func,
        # values,
        # readonly: typing.Optional[typing.Callable[[], bool]] = None,

        # This is just a placeholder for cockpit:
        self.add_setting(
            "force_home", "bool", lambda *args: None, lambda *args: None, None
        )
        print("ZFM2020 Stage does not require initialization.")

    def _move_um(self, target_pos_um, relative=True, verbose=False):
        """
        Moves the stage to the specified position in micrometers.

        Overrides the method to utilize the MCM3000 controller's move function specific to the ZFM2020's configured channel.

        Args:
            target_pos_um (float): The target position in micrometers.
            relative (bool): If True, the movement is relative to the current position.
            verbose (bool): If True, prints detailed movement information.
        """
        # TODO: Take for example this call: it needs to be replaced witha  call to self.conn with the channel that is unique to the stageaxis, i.e. self.channel?
        # this should be repeated for all the move calls, get calls etc.
        # MCM3000Controller.move_um(self, channel=self.channel, move_um=int(target_pos_um), relative=relative, block=True, verbose=verbose)

    def _get_position_um(self, verbose=False):
        """
        Retrieves the current position of the ZFM2020 stage in micrometers.

        Utilizes the MCM3000 controller's functionality to get the current stage position for the configured channel.

        Args:
            verbose (bool): If True, prints detailed position information.

        Returns:
            float: The current stage position in micrometers.
        """
        # return MCM3000Controller.get_position_um(self, channel=self.channel, verbose=verbose)

    def _set_retract_pos_um(
        self, retract_pos_um=None, relative=False, verbose=False
    ):
        """
        Sets the retract position for the ZFM2020 stage in micrometers.

        Utilizes the MCM3000 controller's functionality to set a retract position for the configured channel.

        Args:
            retract_pos_um (float, optional): The retract position in micrometers. If None, uses current position.
            relative (bool): If True, the setting is relative to the current position.
            verbose (bool): If True, prints detailed information about the retract position setting.
        """
        # MCM3000Controller.set_retract_point_um(self, channel=self.channel, retract_pos_um=int(retract_pos_um), relative=relative, verbose=verbose)

    def _get_initial_retract_pos_um(self):
        """
        Retrieves the initial retract position of the ZFM2020 stage in micrometers.

        Uses the MCM3000 controller's functionality to get the retract position for the configured channel.

        Returns:
            float: The initial retract position in micrometers.
        """
        # return MCM3000Controller.get_retract_point_um(self, self.channel)

    def set_velocity_params(self, vel_params, verbose=False):
        """
        Sets the velocity parameters of the Z-stage.

        Args:
            vel_params (dict): A dictionary containing the velocity parameters for the stage.
            verbose (bool): If True, prints detailed information about the operation.
        """
        print(
            f"Velocity parameters cannot be changed on stage {self.stage_name} with controller {self.controller_name}."
        )

    def set_acceleration_params(self, acc_params, verbose=False):
        """
        Sets the acceleration parameters of the Z-stage.

        Args:
            acc_params (dict): A dictionary containing the acceleration parameters for the stage.
            verbose (bool): If True, prints detailed information about the operation.
        """
        print(
            f"Acceleration parameters cannot be changed on stage {self.stage_name} with controller {self.controller_name}."
        )

    def close(self, force=False, verbose=False, simulated=False):
        """
        Closes the ZFM2020 stage controller, ensuring any necessary cleanup is performed.

        Closes the connection and optionally prints a message indicating the closure.

        Args:
            force (bool): Currently unused.
            verbose (bool): If True, prints a message indicating that the stage controller has been closed.
        """
        # TODO: this needs to have the closing of the port reinstated.
        self.shutdown()


if __name__ == "__main__":
    # Example of a successful initialization with valid configuration
    valid_config = {
        "port": "COM3",
        "channel": 1,
        "stage_name": "ZFM2020",
        "reverse": True,
        "verbose": True,
        "very_verbose": True,
        "unit": "mm",
    }

    controller = ZFM2020Stage(valid_config)
    controller.print_info()
    controller.close()
