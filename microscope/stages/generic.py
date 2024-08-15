"""Generic base classes for microscope stages for Oxford Experiments."""

from abc import abstractmethod
from typing import Mapping
import microscope.abc

# Dictionary to map units to their conversion factor to micrometers
unit_conversion_um = {
    "um": 1,
    "mm": 1e3,
    "cm": 1e4,
    "m": 1e6,
    "nm": 1e-3,
    "pm": 1e-6,
}


class _GenericStageAxis(microscope.abc.StageAxis):
    # We are making a generic stage axix here because the methods defined are not dependent on the
    # device manufacturer, we just call the corresponding controller method.
    # TODO: There is the larger question if we want any custom code on here, (i.e. the move by um stuff)
    # or if we put it on the Stage components then we can scrap this baseclass entirely and use a generic StageAxis class.
    def __init__(
        self,
        controller: microscope.abc.Controller,
        name,
        limits=[-10000, 10000],
    ):
        super().__init__()
        self._position = limits[0] + (limits[1] - limits[0]) / 2
        self._limits = limits
        self.controller = controller

    # TODO: This functionality all exists from alvaros code: see below, the relevant stuff just needs ported over to the right call signatures above.
    def move_by(self, delta: float):
        # move the device by a certain amount
        self._position += delta
        # TODO: we will be calling actual methods on the controller classes here and for each of the similar methods.
        # self.controller.move_to(delta, self.channel)

    def move_to(self, pos: float):
        # move the device to a certain position
        self._position = pos

    @property
    def position(self):
        # return position
        return self._position

    @property
    def limits(self):
        # TODO: This should be a named tuple AxisLimits(lower, upper)
        return microscope.AxisLimits(
            lower=self._limits[0], upper=self._limits[1]
        )


class BRamanZStage(microscope.abc.Stage):
    # TODO: Ask alvaro, stage versus stageaxis , stageaxis seems to fit the fact it is 1 axis as opposed to the x_y stage
    # I suspect that it should be a stage with 1 stageaxis but lets see.

    # NOTE(ADW): I think stage is correct, not axis, we shouldnt use axis directly.
    """
    An abstract base class for Z-stages.

    Attributes:
        unit (str): The unit of measurement for stage positions (default is 'um').
        retract_pos_um (float): The retract position of the stage in micrometers.
        stage_name (str): A human-readable name for the stage.
    """

    # TODO: we want to pass in the controller for the stage. i.e. what you do is pass the controller and the channel and that defines how this is moved by accessing self.conn
    def __init__(self, conn: microscope.abc.Controller, **kwargs):
        """
        Initializes a ZStageController object.

        Args:
            unit (str): The unit of measurement for stage positions. Supported units are 'um', 'mm', 'cm', 'm', 'nm', 'pm'.
            stage_name (str): A human-readable name for the stage.
        """
        # self.unit = self.validate_unit(unit)
        # self.retract_pos_um = self._get_initial_retract_pos_um()
        # self.stage_name = stage_name
        super().__init__(**kwargs)
        self.conn = conn
        # TODO: This needs to be changed to a specific subclass of the zstage axis, if we different manufacturers?
        # OR can we make this abc and the _BRamanZStageAxis abstract enough that the implementation in ZFM2020 is all that matters.
        self._axes = {
            "Z": _GenericStageAxis(self.conn, "Z", limits=[-5000, 5000])
        }

        self.homed = False

    # TODO: All this code needs to be moved to the zfm class, its just here to allow an instance to be created.
    # Instead, the abstract methods should be implemented in the zfm class.

    # These are the "Stage" specific methods
    def axes(self):
        return self._axes

    def may_move_on_enable(self):
        # does calling enable move the stage?
        pass

    def shutdown(self):
        self._do_shutdown()

    def _do_shutdown(self) -> None:
        pass

    # NOTE(ADW): We also need a way to access the the StageAxis methods, since this is a single stage we can just access the axis directly
    # but for the X_Y stage we need to be able to access the axis by name.
    def move_by(self, delta: float):
        # move the device by a certain amount
        self._axes["z"].move_by(delta)

    def move_to(self, pos: float):
        # move the device to a certain position
        self._axes["z"].move_to(pos)

    def position(self):
        # return position
        return self._axes["z"].position()

    def limits(self):
        return self._axes[
            "z"
        ].limits()  # TODO: This should be a named tuple AxisLimits(lower, upper)

    @property
    def axes(self):
        return self._axes


class BRamanXYStage(microscope.abc.Stage):
    # TODO: same as above we pass the specific instance of the controller? and the channels which control these axes?
    def __init__(self, conn: microscope.abc.Controller, stage_name="XY Stage"):
        self.stage_name = stage_name
        # we make 2 axes, x and y
        # self.unit = self.validate_unit(unit)
        # self.retract_pos_um = self._get_initial_retract_pos_um()
        # self.stage_name = stage_name
        super().__init__()
        self.conn = conn
        # TODO: I am reusing the _BRamanZStageAxis class here, but this should be a different
        # class for the XY stage OR it should be named _BRamanStageAxis, lean towards the latter.
        self._axes = {
            "X": _GenericStageAxis(self.conn, "X", limits=[4000, 25000]),
            "Y": _GenericStageAxis(self.conn, "Y", limits=[0, 12500]),
        }
        print(self.axes)

    # repeat the same method overloads as zstage.
    @property
    def axes(self):
        return self._axes

    def may_move_on_enable(self):
        pass

    def _do_shutdown(self):
        pass

    def move_by(self, delta: Mapping[str, float]) -> None:
        # TODO: There are large questions about this to be answered, how do we want to move? do we call the stageaxes? do we call the controller.
        print(delta)
        for axis_name, axis_delta in delta.items():
            self._axes[axis_name].move_by(axis_delta)
        # or since we are passing in the controller we can access it but how does this work with cockpit? does it?:
        # for each axis, delta in delta:
        #   self.conn.move_by(delta)

    def move_to(self, pos: Mapping[str, float]) -> None:
        # TODO: The same questions are open here about move_to, by controller or stageaxis?
        print(pos)
        for axis_name, axis_pos in pos.items():
            self._axes[axis_name].move_to(axis_pos)


if __name__ == "__main__":
    stage = BRamanZStage("test")
    x_y_stage = BRamanXYStage("test")
