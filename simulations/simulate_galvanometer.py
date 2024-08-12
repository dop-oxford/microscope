"""Test."""
import microscope
from microscope.device_server import device
from microscope.simulators import (
    SimulatedCamera,
    SimulatedFilterWheel,
    SimulatedLightSource,
    SimulatedStage
)
from microscope.simulators.stage_aware_camera import StageAwareCamera
import numpy as np

DEVICES = [
    device(SimulatedCamera, '127.0.0.1', 8005, {'sensor_shape': (512, 512)}),
    device(SimulatedLightSource, '127.0.0.1', 8006),
    device(SimulatedFilterWheel, '127.0.0.1', 8007, {'positions': 6}),
]

light_source = SimulatedLightSource()
print(light_source.get_status())
print(light_source.get_is_on())

# Instantiate a stage aware camera (this is defined in its own file)
image = np.zeros((2, 3, 4))
print(image.shape[2])
xyz_stage = SimulatedStage({
    'x': microscope.AxisLimits(-5000, 5000),
    'y': microscope.AxisLimits(-10000, 12000),
    'z': microscope.AxisLimits(0, 1000),
})
print(xyz_stage.axes)
filterwheel = SimulatedFilterWheel(positions=4)
camera = StageAwareCamera(image, xyz_stage, filterwheel)
print(camera.get_cycle_time())
print(camera.get_exposure_time())
