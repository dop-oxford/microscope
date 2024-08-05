"""B Raman controller."""
from datetime import datetime
import json
import numpy as np
import os
import pandas as pd
import sys
# Custom modules
import microscope.abc

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from objectives.braman import BRamanObjective
from tube_lenses.braman import BRamanTubeLens
from stages.zfm2020 import ZFM2020Stage
from spectrometers.ibseneagle import IbsenEagleSpectrometer

config = {
    'exc_wl_nm': 785,
    'exc_power_mW': 14,
    'objective': 'N PLAN 10x/0.25',
    'tube_lens': 'WFA4100',
    'z_stage': {
        'stage_name': 'ZFM2020',
        'controller_name': 'MCM3000',
        'port': 'COM3',
        'channel': 1,
        'unit': 'um',
        'reverse': True,
        'verbose': True,
        'very_verbose': False
    },
    'spectrometer': {
        'name': 'IbsenEAGLE',
        'temperature': -60,
        'acquisition_mode': 2,
        'integration_time': 0.5,
        'number_accumulations': 1,
        'number_scans': 1,
        'read_mode': 0,
        'trigger_mode': 0,
        'xpixels': -9999,
        'ypixels': -9999
    }
}
print(config)


# class BRamanController(microscope.abc.Controller):
class BRamanController():

    def __init__(self, config=config, simulated=False):
        """Initialise a new instance of the 'B Raman controller' class."""
        if simulated:
            print('Initialising a simulated B Raman controller')
            self.simulated = True
        else:
            self.simulated = False

        self.units = ['mm', 'mm', 'μm']

        # Define modules and a dictionary of module set-up methods for each
        # supported module
        self.XY_stage = None
        self.Z_stage = None
        self.spectrometer = None
        self.camera = None

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
        self.set_metadata(set_all=True, verbose=True, simulated=simulated)

        print("All INITIALIZED")

    def initialize(self, force=False, verbose=False, module=None):
        """
        Initializes the specified module or all set modules by calling their
        respective initialize methods. If a module has not been set, it will be
        skipped.

        Args:
            force (bool, dict): A flag or dictionary indicating whether to
                forcefully home the modules that can be homed. If a dictionary
                is provided, the specific module's force value will be used; if
                not present in the dictionary, False is assumed.
            verbose (bool): A flag indicating whether to print verbose output
                during the initializing process.
            module (str, optional): Specific module to initialize. If None, all
                modules are initialized.
        """
        modules_to_initialize = [module] if module else \
            self._module_attributes.keys()

        for module_key in modules_to_initialize:
            module_attr = self._module_attributes.get(module_key)
            if module_attr:
                module_instance = getattr(self, module_attr)
                if module_instance:
                    actual_force = force.get(module_key, False) if \
                        isinstance(force, dict) else force
                    module_instance.initialize(actual_force, verbose)
                    if verbose:
                        print(f'{module_key} initialized.')
        print('B Raman INITIALIZED')

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
                setattr(
                    self, self._module_attributes[module_key],
                    self.create_module(module_key, config[module_key])
                )
                print(f'{module_key} SET')
                print('------------------------')
            else:
                print(
                    f'No configuration provided for module: {module_key}. ' +
                    'Attribute set to None.'
                )
                setattr(self, self._module_attributes[module_key], None)
                print(f'Attribute {module_key} set to None.')

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

    def set_metadata(self, set_all=False, verbose=False, simulated=False):
        # The measurement metadata always is updated
        self.set_measurement_metadata(update_all=False, simulated=simulated)
        if set_all:
            self.set_laser_metadata(
                exc_pwr_mW=self.exc_power_mW,
                exc_wl_nm=self.exc_wl_nm,
                update_all=False
            )
            self.set_objective_metadata(update_all=False)
            self.set_imaging_metadata(update_all=False)
            if self.spectrometer:
                self.set_spectro_metadata(update_all=False)
            if self.camera:
                self.set_camera_metadata(update_all=False)
        self.metadata = {
            **self.meas_metadata, **self.laser_metadata,
            **self.objective_metadata, **self.spectro_metadata,
            **self.camera_metadata, **self.imaging_metadata
        }
        if verbose:
            print(self.metadata)

    def set_laser_metadata(
        self, exc_pwr_mW, exc_wl_nm=785, update_all=True, verbose=False
    ):
        # TODO fix error to have the metadata from the attribute
        self.laser_metadata = {
            "Laser power [mW]": exc_pwr_mW,
            "Excitation wavelength [nm]": exc_wl_nm
        }
        if verbose:
            print(self.laser_metadata)
        if update_all:
            self.set_metadata(set_all=False)

    def set_objective_metadata(self, update_all=True, verbose=False):
        self.objective_metadata = self.objective.get_metadata()
        if verbose:
            print(self.objective_metadata)
        if update_all:
            self.set_metadata(set_all=False)

    def set_imaging_metadata(
        self, beam_diam=None, beam_offset=None, update_all=True, verbose=False
    ):
        laser_data = self.read_laser_data()
        self.imaging_metadata = {
            'Magnification': self.objective.get_magnification() *
            self.tube_lens.get_magnification() *
            self.tube_lens.get_focal_length() /
            self.objective.get_f_tube_lens_design(),
        }
        if self.camera:
            self.imaging_metadata['Image_Size'] = (
                np.array(self.camera.get_sensor_size_um()) /
                self.imaging_metadata['Magnification']
            ).tolist()

        if beam_diam is None:
            self.imaging_metadata['spot_size'] = \
                laser_data['spot_size'].values[0]
        else:
            self.imaging_metadata['spot_size'] = beam_diam

        if beam_offset is None:
            self.imaging_metadata['laser_offset'] = [
                laser_data['offset_x'].values[0],
                laser_data['offset_y'].values[0]
            ]
        else:
            self.imaging_metadata['laser_offset'] = beam_offset

        if verbose:
            print(self.imaging_metadata)

        if update_all:
            self.set_metadata(set_all=False)

    def set_tube_lens_metadata(self, update_all=True, verbose=False):
        self.tube_lens_metadata = self.tube_lens.get_metadata()
        if verbose:
            print(self.tube_lens_metadata)
        if update_all:
            self.set_metadata(set_all=False)

    def set_camera_metadata(self, update_all=True, verbose=False):
        self.camera_metadata = self.camera.get_metadata()
        if verbose:
            print(self.camera_metadata)
        if update_all:
            self.set_metadata(set_all=False)

    def read_laser_data(self):
        # Check whether there is data for our current setup
        obj_name = self.objective.get_name()
        tube_name = self.tube_lens.get_name()

        # Hard-code the B Raman beam parameters
        dct = {
            'objective': [
                'UPlanFl', 'HC APO L 63x/0.90 W U-V-I', 'CFI Apo NIR 60X W',
                'N PLAN 100x/0.90', 'N PLAN 10x/0.25', 'N PLAN 10x/0.25_2',
                'EC Epiplan 20x/0.4', 'EC Epiplan 50x/0.75 HD',
                'LD Plan-NEOFLUAR 63X/0.75 Korr',
                'LD EC Epiplan-NEOFLUAR 100x/0.75 HD DIC',
                'EC Epiplan 10x/0.25 HD', 'W "Plan-Apochromat" 63x/1.0',
                'W "N-Achroplan" 20x/0.5', 'W "N-Achroplan" 10x/0.3 M27'
            ],
            'tube_lens': [
                'WFA4100', 'WFA4100', 'WFA4100', 'WFA4100', 'WFA4100',
                'WFA4100', 'WFA4100', 'WFA4100', 'WFA4100', 'WFA4100',
                'WFA4100', 'WFA4100', 'WFA4100', 'WFA4100'
            ],
            'spot_size': [
                None, None, None, None, 80, None, None, None, None, None, None,
                None, None, None
            ],
            'offset_x': [
                None, None, None, None, None, None, None, None, None, None,
                None, None, None, None
            ],
            'offset_y': [
                None, None, None, None, None, None, None, None, None, None,
                None, None, None, None
            ]
        }
        df = pd.DataFrame(dct)

        # Get the parameters for our current setup
        condition = (df['objective'] == obj_name) & \
            (df['tube_lens'] == tube_name)
        data = df[condition]

        # Check the number of rows in the result
        num_rows = data.shape[0]
        # If no rows satisfy the condition, raise an error
        if num_rows == 0:
            msg = f'There is no beam information for objective {obj_name} ' + \
                f'and tube lens {tube_name}.'
            raise Exception(msg)
        # If more than one row satisfies the condition, raise an error
        elif num_rows > 1:
            msg = 'More than one row with information for objective ' + \
                f'{obj_name} and tube lens {tube_name}.'
            raise Exception(msg)

        return data

    def set_measurement_metadata(
        self, update_all=True, verbose=False, simulated=False
    ):
        self.meas_metadata = {
            'DateTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Position [um]': self.get_position(simulated=simulated),
            'Temperature [C]': 'N/A',
            'Humidity [1/100]': 'N/A'
        }
        if self.spectrometer:
            self.meas_metadata['Spectro_Temp [C]'] = \
                self.spectrometer.get_current_temperature()[1]
        if verbose:
            print(self.meas_metadata)
        if update_all:
            self.set_metadata(set_all=False)

    def get_position(self, simulated=False):
        # Returns a 3-dim array with X, Y, and Z positions. If one of those is
        # not active, returns None
        pos = np.array([None, None, None])
        if self.XY_stage:
            pos[0] = self.XY_stage.get_position()[0]
            pos[1] = self.XY_stage.get_position()[1]
            # TODO -> fix this I think is pos[0:2]
        if self.Z_stage:
            pos[2] = self.Z_stage.get_position(simulated=simulated)
        return list(pos)

    def close(self, force=False, verbose=False, module=None):
        """
        Close the specified module or all initialized modules by calling their
        respective close methods. If a module has not been initialized, it will
        be skipped.

        Args:
            force (bool, dict): A flag or dictionary indicating whether to
                forcefully close the modules. If a dictionary is provided, the
                specific module's force value will be used; if not present in
                the dictionary, False is assumed.
            verbose (bool): A flag indicating whether to print verbose output
                during the closing process.
            module (str, optional): Specific module to close. If None, all
                modules are closed.
        """
        modules_to_close = [module] if module else \
            self._module_attributes.keys()

        for module_key in modules_to_close:
            module_attr = self._module_attributes.get(module_key)
            if module_attr:
                module_instance = getattr(self, module_attr)
                if module_instance:
                    actual_force = force.get(module_key, False) if \
                        isinstance(force, dict) else force
                    module_instance.close(actual_force, verbose)
                    if verbose:
                        print(f'{module_key} closed.')
        print('B Raman CLOSED')

    def home(self, force=False, verbose=False, module=None):
        """
        Homes the specified module or all modules by calling their respective
        home methods. If a module has not been set, it will be skipped.

        Args:
            force (bool, dict): A flag or dictionary indicating whether to home
                the modules forcefully, even if they have been already homed.
                If a dictionary is provided, the specific module's force value
                will be used; if not present in the dictionary, False is
                assumed.
            verbose (bool): A flag indicating whether to print verbose output
                during the homing process.
            module (str, optional): Specific module to home. If None, all
                modules are homed.
        """
        modules_to_home = [module] if module else \
            self._module_attributes.keys()

        for module_key in modules_to_home:
            module_attr = self._module_attributes.get(module_key)
            if module_attr:
                module_instance = getattr(self, module_attr)
                if module_instance:
                    actual_force = force.get(module_key, False) if \
                        isinstance(force, dict) else force
                    if hasattr(module_instance, 'home'):
                        module_instance.home(
                            force=actual_force, verbose=verbose
                        )
                        if verbose:
                            print(f'{module_key} homed.')
                    else:
                        print(f'{module_key} does not support homing.')
        print('B Raman HOMED')

    def print_info(self, module=None):
        """
        Print information about the current state of the B-Raman controller.

        Args:
            module (str, optional): Specific module to home. If None, all
            modules are homed.
        """
        modules_to_home = [module] if module else \
            self._module_attributes.keys()

        print('\n---------------------')
        print('---------------------')
        print("B Raman Controller Information:")
        for module_key in modules_to_home:
            module_attr = self._module_attributes.get(module_key)
            if module_attr:
                module_instance = getattr(self, module_attr)
                if module_instance:
                    if hasattr(module_instance, 'print_info'):
                        module_instance.print_info()
                    else:
                        print(f"{module_key} does not support print_info.")
        print('---------------------')
        print('---------------------\n')

    def get_exc_power_mW(self):
        return self.exc_power_mW

    def get_objetive(self):
        return self.objective

    def get_exc_wl_nm(self):
        return self.exc_wl_nm

    def set_exc_power_mW(self, exc_power_mW, verbose=True):
        self.exc_power_mW = exc_power_mW
        if verbose:
            print(f'Excitation power has been set to {self.exc_power_mW} mW')

    def set_objetive(self, objective, verbose=True):
        self.objective = objective
        self.set_objective_metadata(update_all=False)
        if verbose:
            print(f'Objective has been set to {self.objective}')

    def set_tube_lens(self, tube_lens, verbose=True):
        self.tube_lens = tube_lens
        if verbose:
            print(f'Tube Lens has been set to {self.tube_lens}')

    def set_xy_stage(self, config):
        self.set_modules(config['xy_stage'])

    def set_z_stage(self, config):
        self.set_modules(config['z_stage'])

    def set_spectrometer(self, config):
        self.set_modules(config['spectrometer'])

    def set_camera(self, config):
        self.set_modules(config['camera'])

    def set_excitation_power_mW(self, exc_power_mW, verbose=True):
        self.exc_power_mW = exc_power_mW
        if verbose:
            print(f'Excitation power has been set to {self.exc_power_mW} mW')

    def set_excitation_wl_nm(self, exc_wl_nm, verbose=True):
        if exc_wl_nm:
            self.exc_wl_nm = exc_wl_nm
        else:
            msg = 'Please enter laser excitation wavelength in nm: '
            exc_wl_nm = input(msg)
            self.exc_wl_nm = float(exc_wl_nm)
        if verbose:
            print(f'Excitation wavelength has been set to {self.exc_wl_nm} nm')

    def get_image_size_um(self):
        return self.imaging_metadata['Image_Size']

    def get_metadata(self):
        return self.metadata

    def get_image_metadata(self):
        image_metadata = dict(
            Position=self.get_position(),
            Image_size=self.imaging_metadata['Image_Size']
        )
        return image_metadata

    def get_spectrum_df(self):
        return self.spectrometer.get_spectrum_df()

    def set_spectro_metadata(self, update_all=True, verbose=False):
        self.spectro_metadata = self.spectrometer.get_metadata()
        if verbose:
            print(self.spectro_metadata)
        if update_all:
            self.set_metadata(set_all=False)

    def save_spectrum_csv(
        self,
        file_name='Untitled.csv',
        file_path=os.path.dirname(os.path.abspath(__file__))
    ):
        # DataFrame with spectral data:
        df = self.get_spectrum_df()

        # Update the metadata
        self.set_metadata()

        # Convert metadata dictionary to JSON
        json_metadata = json.dumps(self.get_metadata())

        # Create a new DataFrame for the metadata
        df_metadata = pd.DataFrame({'Metadata': [json_metadata]})

        # Concatenate the original DataFrame and the metadata DataFrame
        df = pd.concat([df, df_metadata], ignore_index=True)

        # Write DataFrame to CSV
        df.to_csv(os.path.join(file_path, file_name), index=False)

        return None

    def read_spectrum_csv(self, file_name):
        # Read DataFrame from CSV
        df_data = pd.read_csv(file_name)

        # Extract the metadata JSON string and convert to a dictionary
        # Get last row of Metadata column
        metadata_json = df_data.iloc[-1, df_data.columns.get_loc('Metadata')]
        metadata_dict = json.loads(metadata_json)

        # Remove the metadata row from the DataFrame
        df_data = df_data.drop(df_data.tail(1).index)
        # Remove the metadata column from the DataFrame
        df_data = df_data.drop("Metadata", axis=1)

        return df_data, metadata_dict

    def move(
        self, pos, relative=False, retract=False, units=None, verbose=False
    ):
        if units is None:
            units = self.units
        else:
            if len(units) != 3:
                raise Exception('The units provided are not three!!')
        if retract:
            self.retract_Z()
        self.XY_stage.move(
            target_pos=pos[0:2], relative=relative, units=units[0:2],
            verbose=verbose
        ) 
        self.Z_stage.move(
            0, pos[2], relative=relative, unit=units[2], verbose=verbose
        )
        time.sleep(0.25)
        if verbose:
            time.sleep(.25)
            print(f'B Raman in position {self.get_position()}')

    def move_XY(
        self, pos, relative=False, retract=False, units=None, verbose=False
    ):
        if units is None:
            units = self.units[0:2]
        if len(pos) == 2:
            pass
        elif len(pos) > 3:
            # Ensure that we only take the first two
            pos = pos[0:2]
            print(
                'The position has more than two values, only the first have ' +
                'been considered for the motion be considered.'
            )
        else:
            raise Exception(
                'The position has less than two values, the XY motion cannot '
                'be performed.'
            )
        if retract:
            if self.Z_stage:
                self.retract_Z()
                # TODO -> Integrate that as input
                self.XY_stage.move(
                    target_pos=pos, relative = relative, units = units,
                    verbose=verbose
                )
                time.sleep(0.25)
            else:
                while True:
                    answer = str(input(f'No Z_stage has been initialized, the stage cannot retracted. '
                                  f'Do you want to move without retract? (y/n)')).lower().strip()
                    if answer[0] == 'y' or answer[0] == 'Y':
                        self.XY_stage.move(target_pos=pos, relative = relative, units = units, verbose=verbose)  # TODO -> Integrate that as input
                        time.sleep(0.25)
                        break
                    elif answer[0] == 'n' or answer[0] == 'N':
                        while True:
                            terminate = str(input(f'Do you want to move terminate the program? (y/n)')).lower().strip()
                            if terminate[0] == 'y' or terminate[0] == 'Y':
                                self.close()
                                break
                            elif terminate[0] == 'n' or terminate[0] == 'N':
                                break
                            else:
                                print("Invalid input. Please enter 'y' or 'n'.")
                        break
                    else:
                        print("Invalid input. Please enter 'y' or 'n'.")
        else:
            self.XY_stage.move(target_pos=pos, verbose=verbose)  # TODO -> Integrate that as input
            time.sleep(0.25)
        if verbose:
            time.sleep(.25)
            print(f"B Raman in position {self.get_position()}")


    # def move_Z(self, pos, relative = False, unit=None, verbose = False):
    #     if unit is None:
    #         unit = self.units[2]
    #     self.Z_stage.move(pos, relative = relative, unit=unit, verbose = verbose) 
    #     time.sleep(0.05)
    #     if verbose:
    #         print(f"B Raman in position {self.get_position()}")


    # def move_DZ(self, dZ, unit=None, verbose = False):
    #     if unit is None:
    #         unit = self.units[2]
    #     self.move_Z(dZ, relative = True, unit=unit, erbose = verbose) 


    # def retract_Z(self, verbose = False):
    #     self.Z_stage.retract(verbose=verbose)


    # def set_retract_Z(self, retract_pos=None, relative=False, unit=None, verbose = False):
    #     if unit is None:    
    #         unit = self.units[2]
    #     if retract_pos is None:
    #         retract_pos = self.get_Z_position()
    #     self.Z_stage.set_retract(retract_pos=retract_pos, relative=relative, unit=unit, verbose = verbose)

    # def get_Z_position(self):
    #     if self.Z_stage:
    #         return self.Z_stage.get_position()
    #     else:
    #         raise Exception('No Z stage has been defined.')

    # def get_XY_position(self):
    #     pos = np.array([None, None])
    #     if self.XY_stage:
    #         pos[0] = self.XY_stage.get_position()[0]
    #         pos[1] = self.XY_stage.get_position()[1]  # TODO -> fix this I think is pos[0:2]
    #         return pos
    #     else:
    #         raise Exception('No XY stage has been defined.')

    # def camera_live(self, root = None):
    #     self.camera.live_image(root)

    # def get_image(self, color=True):
    #     return self.camera.get_image(color=color)

    # def save_image(self, name, format = 'png', folder_path = '', w_metadata = True):
    #     if w_metadata:
    #         return self.camera.save_image(name=name, format=format, path=folder_path, metadata_dict = self.get_image_metadata())
    #     else:
    #         return self.camera.save_image(name=name, format=format, path=folder_path)

    # def read_image(self, image_path):
    #     return self.camera.read_image(image_path)

    # def show_spectrum(self):
    #     # TODO -> Improve graphics
    #     self.get_spectrum_df().plot(x='Raman Shift [cm-1]', y='Intensity', kind='line')
    #     plt.show()


if __name__ == '__main__':
    # Test the BRamanController class
    print('Testing BRamanController class...')
    brc = BRamanController(simulated=True)
    brc.print_info()
    brc.close(verbose=True)
