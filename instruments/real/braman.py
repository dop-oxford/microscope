import os
import logging
from microscope.device_server import device
from microscope.simulators import SimulatedCamera
from microscope.controllers.mcm3000 import MCM3000Controller
from microscope.stages.zfm2020 import ZFM2020Stage
from microscope.stages.mls2032 import MLS2032Stage
from microscope.cameras.CS165camera import CS165CUCamera, CS165CUBRCamera


DEVICES = [
    device(
        CS165CUCamera,
        host="127.0.0.1",
        port=8000,
        conf={
            "relative_path_to_dlls": os.path.join(
                "cameras", "_thorlabs", "dlls", "64_lib"
            ),
            "camera_name": "CS165CUCamera_Name",
            "ini_acq": False, 
            "logger_level": logging.DEBUG,
            "simulated": False,
        },
    )
]
