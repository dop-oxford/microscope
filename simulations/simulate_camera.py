from microscope.device_server import device
from microscope.simulators import SimulatedCamera

DEVICES = [
    device(
        SimulatedCamera,
        host="127.0.0.1",
        port=8000,
        conf={"sensor_shape": (512, 512)}
        )
]