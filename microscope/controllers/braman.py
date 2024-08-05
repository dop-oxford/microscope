"""B Raman controller."""
from datetime import datetime
# Custom modules
import microscope.abc

import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from objectives.braman import BRamanObjective
from tube_lenses.braman import BRamanTubeLens
from stages.zfm2020 import ZFM2020Stage
from spectrometers.ibseneagle import IbsenEagleSpectrometer

config = {
    "exc_wl_nm": 785,
    "exc_power_mW": 14,
    "objective": "N PLAN 10x/0.25",
    "tube_lens": "WFA4100",
    "z_stage": {
        "stage_name": "ZFM2020",
        "controller_name": "MCM3000",
        "port": "COM3",
        "channel": 1,
        "unit": "um",
        "reverse": True,
        "verbose": True,
        "very_verbose": False
    },
    # "spectrometer": {
    #     "name": "IbsenEAGLE",
    #     "temperature": -60,
    #     "acquisition_mode": 2,
    #     "integration_time": 0.5,
    #     "number_accumulations": 1,
    #     "number_scans": 1,
    #     "read_mode": 0,
    #     "trigger_mode": 0,
    #     "xpixels": -9999,
    #     "ypixels": -9999
    # }
}

print(config)


# TODO: So the plan here is that this class can stay but it will not be a subclass of anything in microscope:
# What the intended use is that we can use this class to test the other classes that are subclasses of microscope.abc.Controller
# but it will not be part of the "heirarchy".
# This is because there are multiple controllers as part of BRaman,
# 
# The reason this makes sense is that we can configure, x-y stage, z stage, spectrometer etc as microscope classes and then use this class 
# as a way to launch the entire "experiment" at once but there is no use to have this class be part of the micro/cockpit system since 
# we can also define the same setup in our device server file and in our cockpit config.
class BRamanController():
    def __init__(self, config=config):
        self.units = ['mm', 'mm', 'μm']

        # Define modules and a dictionary of module set-up methods for each
        # supported module
        self.XY_stage = None
        self.Z_stage = None
        self.spectrometer = None
        self.camera = None
        self._devices = {}

        self._module_attributes = {
            'xy_stage': 'XY_stage',
            'z_stage': 'Z_stage',
            'spectrometer': 'spectrometer',
            'camera': 'camera',
        }

        # This removes duplicates and preserves the order
        self._supported_module_list = list(
            dict.fromkeys(self._module_attributes.keys())
        )
        print(self._supported_module_list)

        self.check_for_unsupported_modules()

        self.config = config

        # Setup modules based on the provided module list and configuration
        self.set_modules(config)

        # Set the default values for the excitation wavelength, excitation
        # power, objective and tube lens
        if self.config['exc_wl_nm']:
            self.exc_wl_nm = self.config['exc_wl_nm']
        else:
            self.exc_wl_nm = 785
            print(
                'No excitation wavelength was provided. Defaulting to 785 nm.'
            )

        if self.config['exc_power_mW']:
            self.exc_power_mW = self.config['exc_power_mW']
        else:
            self.exc_power_mW = 404
            print('No excitation power was provided. Defaulting to 404 mW.')

        if self.config['objective']:
            print('Objective:', self.config['objective'])
            self.objective = BRamanObjective(self.config['objective'])
        else:
            print('No objective was provided. Defaulting to N PLAN 10x/0.25.')
            self.objective = BRamanObjective('N PLAN 10x/0.25')

        if self.config['tube_lens']:
            print('Tube lens:', self.config['tube_lens'])
            self.tube_lens = BRamanTubeLens(self.config['tube_lens'])
        else:
            print('No tube lens was provided. Defaulting to WFA4100.')
            self.tube_lens = BRamanTubeLens('WFA4100')

        # Define metadata dictionaries
        self.objective_metadata = dict()
        self.meas_metadata = dict()
        self.laser_metadata = dict()
        self.objective_metadata = dict()
        self.spectro_metadata = dict()
        self.camera_metadata = dict()
        self.imaging_metadata = dict()
        self.metadata = dict()
        self.set_metadata(set_all=True, verbose=True)

        print("All INITIALIZED")

    def check_for_unsupported_modules(self):
        """Ensure all modules in module_list are supported."""
        unsupported_modules = [
            module for module in self._supported_module_list
            if module not in self._module_attributes.keys()
        ]
        if unsupported_modules:
            raise ValueError(
                f'Unsupported modules found: {unsupported_modules}. Please ' +
                'check the supported_module_list.'
            )

    def set_modules(self, config):
        """Set up all modules."""
        for module_key in self._supported_module_list:
            if module_key in config:
                print('------------------------')
                print(f'Setting {module_key}...')
                device = self.create_module(module_key, config[module_key])
                setattr(
                    self, self._module_attributes[module_key],
                    device
                )
                self._devices[module_key] = device
                print(f'{module_key} SET')
                print('------------------------')
            else:
                print(
                    f'No configuration provided for module: {module_key}. ' +
                    'Attribute set to None.'
                )
                setattr(self, self._module_attributes[module_key], None)
                print(f'Attribute {module_key} set to None.')
    
    @property
    def devices(self) -> dict:
        print('devices', self._devices)
        return self._devices

    def create_module(self, module_type, config):
        if module_type == 'z_stage':
            stage_name = config['stage_name']
            if stage_name.lower() == 'zfm2020':
                controller_name = config['controller_name']
                if controller_name.lower() == 'mcm3000':
                    return ZFM2020Stage(config, controller='MCM3000')
                else:
                    raise ValueError(
                        f'Unsupported controller name: {controller_name} ' +
                        f'for stage {module_type}'
                    )
            else:
                raise ValueError(
                    f'Unsupported stage name: {stage_name} for module ' +
                    f'{module_type}'
                )

        elif module_type == "xy_stage":
            stage_name = config["stage_name"]
            if (
                stage_name.lower() == "mls203-2"
                or stage_name.lower() == "mls2032_2"
                or stage_name.lower() == "mls20322"
            ):
                controller_name = config["controller_name"]
                if controller_name.lower() == "bbd302":
                    # return MLS2032StageBBD302Controler(config)
                    pass
                else:
                    raise ValueError(
                        f'Unsupported controller name: {controller_name} ' +
                        f'for stage {module_type}'
                    )
            else:
                raise ValueError(
                    f'Unsupported stage name: {stage_name} for module ' +
                    f'{module_type}'
                )

        elif module_type == 'camera':
            name = config['name']
            if name.lower() == 'cs165cu':
                return CS165CUBRCamera(config)
            else:
                raise ValueError(f'Unsupported camera name: {name}')

        elif module_type == 'spectrometer':
            name = config['name']
            if name.lower() == 'ibseneagle':
                print('unimplemented')
                # return IbsenEagleSpectrometer(config)
            else:
                raise ValueError(f'Unsupported spectrometer name: {name}')
        else:
            raise ValueError(f'Unsupported module type: {module_type}')

    def set_metadata(self, set_all=False, verbose=False):
        # The measurement metadata always is updated
        self.set_measurement_metadata(update_all=False)
        print('unimplemented')
        # if set_all:
        #     self.set_laser_metadata(
        #         exc_pwr_mW=self.exc_power_mW, 
        #         xc_wl_nm=self.exc_wl_nm,
        #         update_all=False
        #     )
        #     self.set_objective_metadata(update_all=False)
        #     self.set_imaging_metadata(update_all=False)
        #     if self.spectrometer: self.set_spectro_metadata(update_all=False)
        #     if self.camera: self.set_camera_metadata(update_all=False);
        self.metadata = {
            **self.meas_metadata, **self.laser_metadata,
            **self.objective_metadata, **self.spectro_metadata,
            **self.camera_metadata, **self.imaging_metadata
        }
        if verbose:
            print(self.metadata)

    def set_measurement_metadata(self, update_all = True, verbose = False):
        self.meas_metadata = {
            "DateTime": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "Position [um]": self.get_position(),
            "Temperature [C]": "N/A",
            "Humidity [1/100]": "N/A"
        }
        if self.spectrometer:
            self.meas_metadata['Spectro_Temp [C]'] = self.spectrometer.get_current_temperature()[1]
        if verbose:
            print(self.meas_metadata)
        if update_all:
            self.set_metadata(set_all=False)

    def get_position(self):
        print('unimplemented')
        # # Returns a 3-dim array with X, Y, and Z positions. If one of those is
        # # not active, returns None
        # pos = np.array([None, None, None])
        # if self.XY_stage:
        #     pos[0] = self.XY_stage.get_position()[0]
        #     pos[1] = self.XY_stage.get_position()[1]
        #     # TODO -> fix this I think is pos[0:2]
        # if self.Z_stage:
        #     pos[2] = self.Z_stage.get_position()
        # return list(pos)

if __name__ == '__main__':
    # Test the BRamanController class
    print('Testing BRamanController class...')
    brc = BRamanController()
    import pdb; pdb.set_trace()
