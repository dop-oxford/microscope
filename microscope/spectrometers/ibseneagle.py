"""Controller for the Ibsen Eagle Spectrometer"""
import warnings
import time
import os
import numpy as np

import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from spectrometers.pyAndorSDK2.atmcd import atmcd


class IbsenEagleSpectrometer:
    def __init__(
        self,
        # Set temperature in Celsius
        temperature=-60,
        # Set the acquisition mode to:
        # 1 - 'Single'
        # 2 - 'Accumulate'
        # 3 - Kinetics
        # 4 - Fast Kinetics
        acquisition_mode=2,
        # seconds
        integration_time=0.5,
        # number of accumulations
        number_accumulations=1,
        # number of scans
        number_scans=1,
        # Set readmode to Full Vertical Binning by default
        # 1 = Multitrack
        # 3 = single track
        # 4 = Image
        read_mode=0,
        # Set triggermode to internal
        trigger_mode=0,
        # Initialized with an absurd value instead of nan to begin with
        xpixels=-9999,
        # Initialized with an absurd value instead of nan to begin with
        ypixels=-9999,
    ) -> None:

        # Initialize the Andor ATMCD class
        self.spectrometer = atmcd()
        (ret_code, total_cameras) = self.spectrometer.GetAvailableCameras()

        print(
            f'Detected {total_cameras} available camera(s). If multiple ' +
            'cameras are available, please modify code to enable camera ' +
            'selection (not currently supported in BRaman). ' +
            f'Return code: {ret_code}'
        )

        if total_cameras != 0:
            print('Initializing...')
            # According to documentation, Initialize() needs dir as input,
            # given as 'path to "the files"'. Not sure what "the files" refers
            # to, but works with os.getcwd() as long as package is in the same
            # directory as this file.
            ret_code = self.spectrometer.Initialize(os.getcwd())

            if ret_code != atmcd.DRV_SUCCESS:
                raise RuntimeError(
                    'A spectrometer/camera was found, but could not be ' +
                    f'initialized. Initialization return-code: {ret_code}'
                )

            print('Setting up spectrometer with default parameters')

            # Declaring these variables here (even though they will be repeated
            # shortly), so as to keep a more concise overview of the variables
            # and their initial setpoints.
            self.temperature = temperature
            self.acquisition_mode = acquisition_mode
            self.integration_time = integration_time
            self.number_accumulations = number_accumulations
            self.number_scans = number_scans
            self.read_mode = read_mode
            self.trigger_mode = trigger_mode
            self.xpixels = xpixels
            self.ypixels = ypixels

            # Turn on the cooler
            self.turn_cooler_on()
            self.set_temperature(self.temperature)

            self.set_acquisition_mode(self.acquisition_mode)
            self.set_integration_time(self.integration_time)
            self.set_number_accumulations(self.number_accumulations)
            self.set_number_scans(self.number_scans)
            self.set_read_mode(self.read_mode)
            self.set_trigger_mode(self.trigger_mode)
            self.auto_set_image()

        else:
            raise RuntimeError(
                'No available cameras/spectrometers. Cannot initialize any ' +
                'cameras.'
            )

    def turn_cooler_on(self):
        ret_code = self.spectrometer.CoolerON()
        if ret_code != atmcd.DRV_SUCCESS:
            print(
                'Failed to turn on cooler. Failed with return code: ' +
                f'{ret_code}'
            )
        else:
            print('Cooler turned ON')

    def turn_cooler_off(self):
        ret_code = self.spectrometer.CoolerOFF()
        if ret_code != atmcd.DRV_SUCCESS:
            print(
                'Failed to turn off cooler. Failed with return code: ' +
                f'{ret_code}'
            )
        else:
            print('Cooler turned OFF')

    def set_temperature(self, temperature_setpoint, release=False):
        """
        Set the temperature of the spectrometer.
        :param temperature_setpoint: Temperature, in degrees Celsius
        :param release: If True, it does not wait for the temperature to
        stabilize and if temperature is above setpoint
        the loop is exited immediately
        :return:
        """
        print(
            'Checking cooling and setting temperature setpoint to ' +
            f'{self.temperature}C'
        )

        # This will be the same when called from __init__
        self.temperature = temperature_setpoint

        # Check the cooler is running
        (ret_code, icoolerstatus) = self.spectrometer.IsCoolerOn()

        if ret_code != atmcd.DRV_SUCCESS:
            raise RuntimeError(f'Could not determine current cooler status. Returned code {ret_code}.')

        # If the cooler is not running (for some reason), turn it on
        if icoolerstatus == 0:
            warnings.warn('The cooler was not running. Turning on the cooler', RuntimeWarning)
            self.turn_cooler_on()

        ret_code = self.spectrometer.SetTemperature(self.temperature)

        if ret_code != atmcd.DRV_SUCCESS:
            print(f'The temperature could not be set. Failed with return code: {ret_code}')

        # Potentially a dangerous design-decision. However, the logic is that we do not allow users to run any measurements unless the temperature is completely stabilized. This will ensure better and more reproducible acquisitions. We can add exceptions later if needed.

        print(f'Spectrometer is cooling and/or changing temperature setpoint...')
        if release:
            timeout = time.time() + 60 * 1  # 1 min initial timeout
            print(f'Hold will be released when minimum temperature {temperature_setpoint}C is REACHED')
            while True:
                (ret_code, curr_temperature) = self._get_current_temperature()

                if ret_code == atmcd.DRV_TEMP_NOT_STABILIZED or curr_temperature >= temperature_setpoint or ret_code == atmcd.DRV_TEMP_STABILIZED:
                    print(f'Release temperature has been reached. Spectrometer released with T {curr_temperature}C')
                    break
                elif ret_code == atmcd.DRV_TEMP_NOT_REACHED:
                    pass
                    #print(f'Current temperature {curr_temperature}. Status: DRV_TEMP_NOT_REACHED')
                if time.time() > timeout:
                    while True:
                        reply = str(input(f'Current temperature {curr_temperature}C. Want to release? (y/n)')).lower().strip()
                        if reply[0] == 'y':
                            break
                        elif reply[0] == 'n':
                            timeout = time.time() + 60  # 60s timeout min timeout
                            break
                        else:
                            print("Only y or n is accepted as an answer")
                    if reply[0] == 'y':
                        break
                time.sleep(5)
        else:
            print(f'Hold will be released when temperature {temperature_setpoint}C is STABILIZED')
            timeout = time.time() + 60 * 0  # 0 min initial timeout
            while True:
                (ret_code, curr_temperature) = self._get_current_temperature()
                if ret_code == atmcd.DRV_TEMP_NOT_REACHED:
                    print(f'Current temperature {curr_temperature}. Status: DRV_TEMP_NOT_REACHED')
                elif ret_code == atmcd.DRV_TEMP_NOT_STABILIZED:
                    print(f'Current temperature {curr_temperature}. Status: DRV_TEMP_NOT_STABILIZED')
                elif ret_code == atmcd.DRV_TEMP_STABILIZED:
                    print(f'Stabilized at current temperature {curr_temperature}.')
                    break
                if time.time() > timeout:
                    while True:
                        reply = str(input(f'Current temperature {curr_temperature}. Not stabilized. Want to move on? (y/n)')).lower().strip()
                        if reply[0] == 'y':
                            break
                        elif reply[0] == 'n':
                            timeout = time.time() + 30 # 30s timeout min timeout
                            break
                        else:
                            print("Only y or n is accepted as an answer")
                    if reply[0] == 'y':
                        break
                time.sleep(10)

        print('Hold was released')

    def set_acquisition_mode(self,acquisition_id):
        self.acquisition_mode = acquisition_id
        ret_code = self.spectrometer.SetAcquisitionMode(self.acquisition_mode)
        if ret_code != atmcd.DRV_SUCCESS:
            print(f'Failed to set acquisition mode. Failed with return code: {ret_code}')
        else:
            print(f'Acquisition mode set to: {self.acquisition_mode}') 

    def set_integration_time(self, integration_setpoint):
        self.integration_time = integration_setpoint
        ret_code = self.spectrometer.SetExposureTime(self.integration_time)
        if ret_code != atmcd.DRV_SUCCESS:
            print(f'Failed to set integration time. Failed with return code: {ret_code}')
        else:
            print(f'Integration time set to: {self.integration_time} s')

    def set_number_accumulations(self, accumulations_setpoint):
        self.number_accumulations = accumulations_setpoint
        ret_code = self.spectrometer.SetNumberAccumulations(self.number_accumulations)
        if ret_code != atmcd.DRV_SUCCESS:
            print(f'Failed to set number of accumulations. Failed with return code: {ret_code}')
        else:
            print(f'Number of accumulations set to: {self.number_accumulations}')

    def set_number_scans(self, number_scans):
        # This function will set the number of scans (possibly accumulated
        # scans) to be taken during a single acquisition sequence.
        # This will only take effect if the acquisition mode is Kinetic Series.
        self.number_scans = number_scans
        ret_code = self.spectrometer.SetNumberKinetics(self.number_scans)
        if ret_code != atmcd.DRV_SUCCESS:
            print(f'Failed to set number of scans. Failed with return code: {ret_code}')
        else:
            print(f'Number of accumulations set to: {self.number_accumulations}')

    def set_read_mode(self, read_mode_id):
        self.read_mode = read_mode_id
        ret_code = self.spectrometer.SetReadMode(self.read_mode)
        if ret_code != atmcd.DRV_SUCCESS:
            print(f'Failed to set read mode. Failed with return code: {ret_code}')
        else:
            print(f'Read mode set to set to: {self.read_mode}') 

    def set_trigger_mode(self, trigger_mode_id):
        self.trigger_mode = trigger_mode_id
        ret_code = self.spectrometer.SetTriggerMode(self.trigger_mode)
        if ret_code != atmcd.DRV_SUCCESS:
            print(f'Failed to set trigger mode. Failed with return code: {ret_code}')
        else:
            print(f'Trigger mode set to: {self.trigger_mode}') 

    def auto_set_image(self):
        (ret_code, self.xpixels, self.ypixels) = self.spectrometer.GetDetector()
        if ret_code != atmcd.DRV_SUCCESS:
            print(f'Failed to run GetDetector. Failed with return code: {ret_code}')
        else:
            print(f'GetDetector yielded xpixels: {self.xpixels}, and ypixels {self.ypixels}')

        ret_code = self.spectrometer.SetImage(1, 1, 1, self.xpixels, 1, self.ypixels)
        if ret_code != atmcd.DRV_SUCCESS:
            print(f'Failed to Set image. Failed with return code: {ret_code}')
        else:
            print(f'Auto-set image completed')

    def get_integration_time(self):
        return self.integration_time

    def get_number_accumulations(self):
        return self.number_accumulations

    def get_current_temperature(self):
        return self._get_current_temperature()[1]

    def _get_current_temperature(self):
        (ret_code, curr_temperature) = self.spectrometer.GetTemperature()
        return (ret_code,curr_temperature)

    def get_temperature_setpoint(self):
        return self.temperature

    def get_acquisition_mode(self):
        return self.acquisition_mode

    def get_read_mode(self):
        return self.read_mode

    def get_trigger_mode(self):
        return self.trigger_mode

    def get_metadata(self): 
        spectro_metadata = {
            "Spectrometer integration time [s]": self.get_integration_time(),
            "Spectrometer number of accumulations": self.get_number_accumulations(),
            "Spectrometer temperature [C]": self.get_current_temperature(),
            "Spectrometer acquisition mode": self.get_acquisition_mode(),
            "Spectrometer read mode": self.get_read_mode(),
            "Spectrometer trigger mode": self.get_trigger_mode()
        }
        return spectro_metadata
    
    def get_raw_spectrum(self):
        self.spectrometer.prepare_fvb_scan()
        return np.flip(np.asarray(self.spectrometer.acquire_fvb_scan())) # The flip is necessary to match first
    
    def print_info(self):
        # Retrieve the spectrometer parameters.
        params = self.get_metadata()
        # Print each parameter in a formatted manner.
        print("Spectrometer Parameters:")
        for key, value in params.items():
            print(f"{key}: {value}")


    def prepare_fvb_scan(self):
        
        # Ensure the read mode is correct
        self.set_read_mode(0)
        self.auto_set_image() # Make sure this is set before acquiring the data
        ret_code = self.spectrometer.PrepareAcquisition()
        if ret_code != atmcd.DRV_SUCCESS:
            print(f'Failed to prepare acquisition. Failed with return code: {ret_code}')
        else:
            print(f'Acquisition prepared...') 

    def acquire_fvb_scan(self):
        # First check that the camera status is IDLE
        status = self.get_camera_status()
        if status == atmcd.DRV_IDLE:
            ret_code = self.spectrometer.StartAcquisition()
            if ret_code != atmcd.DRV_SUCCESS:
                print(f'Failed to start acquisition. Failed with return code: {ret_code}')
            ret_code = self.spectrometer.WaitForAcquisition()
            if ret_code != atmcd.DRV_SUCCESS:
                print(f'Failed to wait for new data acquisition. Failed with return code: {ret_code}')
            (ret_code, image_data) = self.spectrometer.GetMostRecentImage(self.xpixels)
            if ret_code != atmcd.DRV_SUCCESS:
                print(f'Failed to acquire data. Failed with return code: {ret_code}')
            else:
                return image_data
        else:
            print(f'Spectrometer was not ready to acquired. Returned status: {status}, expected: {atmcd.DRV_IDLE}')
            return None

    def prepare_image_scan(self):
        self.set_read_mode(4)
        self.auto_set_image() # Make sure this is set before acquiring the data
        ret_code = self.spectrometer.PrepareAcquisition()
        if ret_code != atmcd.DRV_SUCCESS:
            print(f'Failed to prepare acquisition. Failed with return code: {ret_code}')
        else:
            print(f'Acquisition prepared...') 

    def acquire_image_scan(self):
        # First check that the camera status is IDLE
        status = self.get_camera_status()
        if status != atmcd.DRV_IDLE:
            ret_code = self.spectrometer.StartAcquisition()
            if ret_code != atmcd.DRV_SUCCESS:
                print(f'Failed to start acquisition. Failed with return code: {ret_code}')
            ret_code = self.spectrometer.WaitForAcquisition()
            if ret_code != atmcd.DRV_SUCCESS:
                print(f'Failed to wait for new data acquisition. Failed with return code: {ret_code}')
            (ret_code, image_data) = self.spectrometer.GetMostRecentImage(self.xpixels * self.ypixels)
            if ret_code != atmcd.DRV_SUCCESS:
                print(f'Failed to acquire data. Failed with return code: {ret_code}')
            else:
                return image_data
        else:
            print(f'Spectrometer was not ready to acquired. Returned status: {status}, expected: {atmcd.DRV_IDLE}')
            return None

    def get_camera_status(self):
        (ret_code, status) = self.spectrometer.GetStatus()
        if ret_code != atmcd.DRV_SUCCESS:
            print(f'Failed to get spectrometer status. Failed with return code: {ret_code}')
            return None
        return status

    def release_spectrometer(self):
        print('Releasing spectrometer (overriding temperature settings).')
        print(
            'Imposing hold. Hold will be released when temperature is' +
            'stabilized and safe for shutdown.'
        )
        self.set_temperature(-15, release=True)
        ret_code = self.turn_cooler_off()

    def shutdown(self):
        print('Shutting down the spectrometer')
        ret_code = self.spectrometer.ShutDown()
        if ret_code != atmcd.DRV_SUCCESS:
            raise RuntimeError(
                'The spectrometer could not be shut down. Returned code ' +
                f'{ret_code}.'
            )
        elif ret_code == atmcd.DRV_SUCCESS:
            print('The spectrometer has been shut down.')


if __name__ == '__main__':
    handle = IbsenEagleSpectrometer()
    print(handle.get_metadata())
    handle.release_spectrometer()
    handle.shutdown()
