
from base_spectrometer import BRamanSpectrometer
from spectrometers.ibseneagle_spectrometer import IbsenEagleSpectrometer

import pandas as pd
import os
from pathlib import Path

calibration_path = os.path.join(Path(__file__).resolve().parents[4], 'calibration')
pixel_to_wavelength_file_path = os.path.join(calibration_path,'IbsenEagleSpectrometer_PixeltoWavelength.csv')


class IbsenEagleBRSpectrometer(BRamanSpectrometer, IbsenEagleSpectrometer):
    def __init__(self, config):
        BRamanSpectrometer.__init__(self,config)
        IbsenEagleSpectrometer.__init__(self,
                 temperature = self.config.get('temperature', -60),  # Set the temperature to -60 degrees by default
                 acquisition_mode = self.config.get('acquisition_mode', 2),  # Set acquisition mode to 2 by default
                 integration_time = self.config.get('integration_time', 0.1),  # Set integration time to 0.1 s by default
                 number_accumulations = self.config.get('number_accumulations', 1),  # Set number of accumulations to 1 by default
                 number_scans = self.config.get('number_scans', 1),  # Set number of scans to 1 by default
                 read_mode = self.config.get('read_mode', 0),  # Set read mode to 0 by default
                 trigger_mode = self.config.get('trigger_mode', 0),  # Set trigger mode to 0 by default
                 xpixels = self.config.get('xpixels', -9999),  # Set number of x pixels to -9999 by default
                 ypixels = self.config.get('ypixels', -9999),  # Set number of y pixels to -9999 by default
                 )
        self.spectrum_units_df = pd.read_csv(pixel_to_wavelength_file_path)
        self.spectrum_units_df['Raman Shift [cm-1]'] = 1e7*(1/self.exc_wl_nm-1/self.spectrum_units_df['Wavelength [nm]'])
        
    def print_info(self):
        """
        Prints information about the spectrometer.
        """
        IbsenEagleSpectrometer.print_info(self)
    

    def _initialize(self, verbose=True):
        """
        Initializes the spectrometer.

        Prepares the spectrometer for operation, which is not needed in this case.
        
        """
        print(f"Spectrometer {self.name} already initialized.")


    def _close(self, force=False, verbose=True):
        """
        Closes the spectrometer, ensuring any necessary cleanup is performed.

        Args:
            force (bool): Forces closure without releasing to high temperature. Defaults to False.
            verbose (bool): If True, enables verbose output during the operation.
        """
        if not force: IbsenEagleSpectrometer.release_spectrometer(self)
        IbsenEagleSpectrometer.shutdown(self)

  
    def get_current_temperature():
        return IbsenEagleSpectrometer.get_current_temperature(self)

    def get_metadata(self):
        return IbsenEagleSpectrometer.get_metadata(self)

    def get_spectrum_df(self):
        if self.name == 'IbsenEagle':
            df = self.spectrum_units_df 
            df['Intensity'] = self.get_raw_spectrum()
        else:
            raise Exception(f'Unrecognized spectrometer model {self.spectro_model}')
        return df
    

if __name__ == '__main__':
    print(pixel_to_wavelength_file_path)