from microscope.device_server import device
from microscope.simulators import SimulatedCamera
from microscope.controllers.mcm3000 import MCM3000Controller
from microscope.stages.zfm2020 import ZFM2020Stage
from microscope.stages.mls2032 import MLS2032Stage
from microscope.cameras.CS165camera import CS165CUCamera, CS165CUBRCamera


DEVICES = [
    device(
        SimulatedCamera,
        host="127.0.0.1",
        port=8000,
        conf={"sensor_shape": (512, 512)}
        ),
    device(
        ZFM2020Stage,
        host="127.0.0.1",
        port=8001,
        conf= {
                "port": "COM3",
                "channel": 1,
                "stage_name": "ZFM2020",
                "reverse": True,
                "verbose": True,
                "very_verbose": True,
                "unit": "mm"
            }
    ),
    device(
        MLS2032Stage,
        host="127.0.0.1",
        port=8002,
        conf= {
            "port": "COM4",
            "channel": 1,
            "stage_name": "MLS2032",
            "reverse": True,
            "unit": "mm"
        }
    ),
    device(
        CS165CUCamera,
        host="127.0.0.1",
        port=8003,
        conf= {
            "relative_path_to_dlls": os.path.join(
                "cameras", "_thorlabs", "dlls", "64_lib"
            ),
            "simulated": True,
        }
    ),
    device(
        CS165CUBRCamera,
        host="127.0.0.1",
        port=8004,
        conf= {
            "relative_path_to_dlls": os.path.join(
                "cameras", "_thorlabs", "dlls", "64_lib"
            ),
            "simulated": True,
        }
    )
]