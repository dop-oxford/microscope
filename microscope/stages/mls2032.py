from microscope.stages.generic import BRamanXYStage


class MLS2032Stage(BRamanXYStage):
    def __init__(self, *args, **kwargs):
        # TODO: Add the controller as a kwarg.
        super().__init__("test_controller")
        self.initialize()

    # NOTE: It makes sense from Alvaros comments that we call self.conn in this class.

    def initialize(
        self,
        home=True,
        force_home=False,
        max_vel=None,
        acc=None,
        verbose=False,
    ):
        """Initializes the XY stage with given parameters.

        Args:
            max_vel (float): Maximum velocity for the stage movement.
            acc (float): Acceleration for the stage movement.
            force_home (bool): If True, forces the stage to home even if it's already homed.
            verbose (bool): If True, enables verbose output during operation.

        """

        # TODO: these settings can all be done with add_setting I give examples below:
        # NOTE(ADW): here that i am passing empty lambdas but these are the getter and setter methods
        self.add_setting(
            "force_home",
            "bool",
            lambda *args: None,
            lambda *args: None,
            lambda *args: [True, False],
        )
        self.set_setting("force_home", False)
        # self.add_setting('max_vel', "float", lambda *args: None, lambda *args: None, None)
        # self.set_setting('max_vel', max_vel)
        # if max_vel is not None or acc is not None: TO BE REMOVED
        #     self.set_velocity_params(channel=None, max_vel=max_vel, acc=acc, verbose=verbose)

    # TODO: For things like this we can be calling the controller but I can't see if this is necessary
    def set_velocity_params(
        self, channel=None, max_vel=None, acc=None, verbose=False
    ):
        """Sets the velocity and acceleration parameters of the XY stage.

        Args:
            channel (list or None, optional): List of channel names or numbers. If None, sets parameters for all channels. Defaults to None.
            max_vel (float or None, optional): Maximum velocity. Defaults to None.
            acc (float or None, optional): Acceleration. Defaults to None.
            verbose (bool, optional): Whether to print additional information. Defaults to False.

        """
        # BBD30XController.set_velocity_params(self, channel, max_vel, acc, verbose)

    def move_mm(
        self, target_pos, channel, relative, max_vel, acc, permanent, verbose
    ):
        """Moves the XY stage to a specified end position.

        Args:
            target_pos (list/tuple): A tuple specifying the target X and Y positions.
            channel (list/tuple or None, optional): List of channel names or numbers. If None, moves all channels. Defaults to None.
            max_vel (float or None, optional): Maximum velocity for all channels. Defaults to None.
            acc (float or None, optional): Acceleration for all channels. Defaults to None.
            permanent (bool, optional): Whether to make velocity and acceleration changes permanent. Defaults to False.
            verbose (bool, optional): Whether to print additional information. Defaults to False.

        """
        # BBD30XController.moveTo(self, target_pos=target_pos, channel=channel, relative=relative, max_vel=max_vel, acc=acc, permanent=permanent, verbose=verbose)

    def home(self, force_home=False, verbose=False):
        """Homes the XY stage.

        Args:
            force_home (bool): If True, forces the stage to home regardless if it is homed already or not.
            verbose (bool): If True, enables verbose output during the homing operation.

        """
        # BBD30XController.home_channels(self, channel=None, force=force_home, verbose=verbose)

    def get_position(self):
        """Gets the current position of the XY stage.

        Returns:
            tuple: The current X and Y position of the stage.

        """
        # BBD30XController.get_position(self)

    def close(self, force, verbose):
        """Cleans up and releases resources of the XY stage.

        Args:
            force (bool): If True, forces the stage to close regardless of its current state.
            verbose (bool): If True, enables verbose output during cleanup.

        """
        # BBD30XController.finish(self, verbose=verbose)


if __name__ == "__main__":
    stage = MLS2032Stage()
    x = stage.get_all_settings()
    print(x)
