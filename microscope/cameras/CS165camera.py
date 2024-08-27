import warnings
import microscope.abc

import warnings
import os
from pathlib import Path
import logging
import time

from microscope.cameras._thorlabs.tl_camera import (
    TLCameraSDK,
    TLCamera,
    Frame,
    OPERATION_MODE,
    ROI,
)
from microscope.cameras._thorlabs.tl_camera_enums import SENSOR_TYPE
from microscope.cameras._thorlabs.tl_mono_to_color_processor import (
    MonoToColorProcessorSDK,
)
from microscope.cameras._thorlabs.tl_mono_to_color_enums import COLOR_SPACE
from microscope.cameras._thorlabs.tl_color_enums import FORMAT
from microscope.simulators import _ImageGenerator
import numpy as np
import os
import json
from PIL import Image, PngImagePlugin
import threading
import queue

_logger = logging.getLogger(__name__)

# TODO: This needs serious investigation, I am just using another piece of code but i cant find similar code in SDK
# NOTE(ADW): The rising edge seems to be trigger polarity on the SDK and the TLCAMERA.operation_mode is trigger
# mode, se we should be passing these tuples to those setters respectively.
STRING_TO_TRIGGER = {
    "external": (
        microscope.TriggerType.RISING_EDGE,
        microscope.TriggerMode.ONCE,
    ),
    "external exposure": (
        microscope.TriggerType.RISING_EDGE,
        microscope.TriggerMode.BULB,
    ),
    "software": (microscope.TriggerType.SOFTWARE, microscope.TriggerMode.ONCE),
}


class CS165CUCamera(microscope.abc.Camera):
    """
    Class to control the Thorlabs CS165CU Camera
    """

    def __init__(
        self,
        relative_path_to_dlls=None,
        camera_number=None,  # The number in the list of cameras of the camera we want to get
        camera_name=None,  # Name of camera
        ini_acq=False,  # Whether to initialize the acquisition with the default values
        verbose=True,  # If True, info in printed in terminal
        very_verbose=False,
        simulated=False,
    ):  # If True, more info in printed in terminal
        super().__init__()
        self._gain = 0
        self.add_setting(
            "gain",
            "int",
            lambda: self._gain,
            self._set_gain,
            lambda: (0, 8192),
        )

        self.relative_path_to_dlls = relative_path_to_dlls
        self.simulated = simulated
        self.verbose = verbose
        self.very_verbose = very_verbose
        self.camera_name = camera_name

        # TODO: we can't hard set the trigger mode really
        self._trigger_mode = "software"
        self._acquiring = False
        self._triggered = 0
        self._sent = 0

        # default values for sdk, camera list and camera 
        self.sdk = {}
        self.camera_list = None
        self.camera = {}

        self._is_color = (
            False  # TODO: This is a hack that needs removed later.
        )

        if self.simulated:
             # simulated camera
            self._simulated_settings = {
                'sensor_shape': (512, 512),
                'roi': microscope.ROI(0, 0, 512, 512),
                'exposure_time': 0.1
            }
            self._image_generator = _ImageGenerator()

            self.add_setting(
                "image pattern",
                "enum",
                self._image_generator.method,
                self._image_generator.set_method,
                self._image_generator.get_methods,
            )
            self.add_setting(
                "image data type",
                "enum",
                self._image_generator.data_type,
                self._image_generator.set_data_type,
                self._image_generator.get_data_types,
            )
            self.add_setting(
                "display image number",
                "bool",
                lambda: self._image_generator.numbering,
                self._image_generator.enable_numbering,
                None,
            )
            return

        # real camera
        if not self.relative_path_to_dlls:
            raise ValueError(
                "Relative path to DLLs must be provided for simulated camera."
            )
        try:
            # setup the path to the DLLs
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            absolute_path_to_dlls = os.path.join(project_root, relative_path_to_dlls)
            os.environ['PATH'] = absolute_path_to_dlls + os.pathsep + os.environ['PATH']
            os.add_dll_directory(absolute_path_to_dlls)
        except Exception as exception:
            _logger.error("Could not set path to DLLs: %s", str(exception))
            raise exception

        try: 
            # initialize the SDK
            # TODO: This is a hack that needs removed later.
            self.sdk = TLCameraSDK()
        except Exception as exception:
            _logger.error("SDK not initialised: %s", str(exception)) 
            raise exception

        try:
            # get the camera list
            self.camera_list = self.sdk.discover_available_cameras()
            print(f"Cameras found: {self.camera_list}")
        except Exception as exception:
            _logger.error("No cameras have been found: %s", str(exception))
            raise exception

        if camera_number:
            self.camera = self.sdk.open_camera(self.camera_list[camera_number])
        else:
            if len(self.camera_list) == 1:
                self.camera = self.sdk.open_camera(self.camera_list[0])
            else:
                # Select camera from list
                print(self.camera_list)
                try:
                    user_input = int(
                        input(
                            f"Enter integer of the camera that needs to be selected: "
                        )
                    )
                    if 0 <= user_input <= len(self.camera_list) - 1:
                        self.camera = self.sdk.open_camera(
                            self.camera_list[user_input]
                        )
                    else:
                        print(
                            f"Input should be an integer between 0 and {len(self.camera_list) - 1}. Try again."
                        )
                except ValueError:
                    print("Invalid input. Please enter an integer.")

        # setup color processing if necessary
        if self.camera.camera_sensor_type != SENSOR_TYPE.BAYER:
            # Sensor type is not compatible with the color processing library
            self._is_color = False
        else:
            self.mono_to_color_sdk = MonoToColorProcessorSDK()
            self.initialize_mono_to_color_processor()
            self.set_color_processor_properties()
            self._is_color = True

        # State that the acquisition has not been initialized
        self.acq_initialized = False
        if ini_acq:
            self.initialize_acquisition()

        # Set metadata information
        self.set_metadata()

    def _do_enable(self):
        _logger.info("Preparing for acquisition.")
        if self._acquiring:
            self.abort()
        self._acquiring = True
        self._sent = 0
        _logger.info("Acquisition enabled.")
        return True

    # TODO: This is placeholder code:: Ask alvaro if the frame_rate_control_value is this cycle time
    def get_cycle_time(self):
        """
        Get the current cycle time from the camera.
        
        :return: The current cycle time in seconds.
        :rtype: float
        """
        if self.simulated:
            return self._simulated_settings.get('cycle_time', 0.2)  # Default simulated cycle time
        try:
            return self.camera.frame_rate_control_value
        except Exception as exception:
            _logger.error("Could not get cycle time; " + str(exception))
            raise exception
        
    def set_cycle_time(self, cycle_time_value):
        """
        Set the cycle time for the camera.
        
        :param cycle_time_value: The desired cycle time in seconds.
        :type: float
        """
        if self.simulated:
            self._simulated_settings['cycle_time'] = cycle_time_value
        else:
            try:
                self.camera.frame_rate_control_value = cycle_time_value
            except Exception as exception:
                _logger.error("Could not set cycle time; " + str(exception))
                raise exception

    # TODO: cant imagine this wont need more work
    def soft_trigger(self):
        self._do_trigger()

    def _do_shutdown(self):
        """Cleans up the TLCameraSDK and TLCamera instances."""
        if self.simulated:
            return
        if self._is_color:
            try:
                self.mono_to_color_processor.dispose()
            except Exception as exception:
                print(
                    f"Unable to dispose Mono to Color processor: {exception}"
                )
            try:
                self.mono_to_color_sdk.dispose()
            except Exception as exception:
                print(f"Unable to dispose Mono to Color SDK: {exception}")
        try:
            self.camera.dispose()
        except Exception as exception:
            print(f"Unable to dispose TLCamera: {exception}")
        try:
            self.sdk.dispose()
        except Exception as exception:
            print(f"Unable to dispose TLCamera_SDK: {exception}")

    def abort(self):
        """Aborts the camera acquisition."""
        # TODO: work out how to do this. I suspect it is with disarm
        self.camera.disarm()

    def rename_camera(self, camera_name):
        """Renames the camera.

        Args:
            camera_name (str): New name for the camera.
        """
        try:
            self.camera.name = camera_name
        except Exception as error:
            print(
                f"Encountered error: {error}, camera name could not be set to {camera_name}."
            )
            self.dispose()
        if self.verbose:
            print(f"Camera name has been set to {camera_name}.")

    def _get_sensor_shape(self):
        """Returns sensor dimensions in pixels.

        Returns:
            list: Sensor dimensions [height, width] in pixels.
        """
        if self.simulated:
            return self._simulated_settings.get('sensor_shape', [512, 512])  # Default simulated sensor shape
        return [
            self.camera.image_height_pixels,
            self.camera.image_width_pixels,
        ]
    
    def get_pixel_size(self):
        """Returns pixel dimensions in micrometers (um).

        Returns:
            list: Pixel dimensions [height, width] in micrometers (um).
        """
        if self.simulated:
            return self._simulated_settings.get('pixel_size', [6.5, 6.5])  # Default simulated pixel size in um
        return [
            self.camera.sensor_pixel_height_um,
            self.camera.sensor_pixel_width_um,
        ]

    def get_sensor_size_um(self):
        """Returns sensor dimensions in micrometers (um).

        Returns:
            list: Sensor dimensions [height, width] in micrometers (um).
        """
        return (
            np.array(self._get_sensor_shape())
            * np.array(self.get_pixel_size())
        ).tolist()

    def set_metadata(self):
        """Sets camera metadata."""
        self.metadata = dict(
            Camera_Sensor_Size_HxW=self._get_sensor_shape(),
            Camera_Pixel_Size_HxW=self.get_pixel_size(),
        )

    def get_metadata(self):
        """Returns camera metadata.

        Returns:
            dict: Camera metadata dictionary.
        """
        return self.metadata

    # --- Color processing functions ---
    def initialize_mono_to_color_processor(self):
        """Initializes mono to color processor if the camera is color."""
        if not hasattr(self, "mono_to_color_processor"):
            setattr(self, "mono_to_color_processor", None)
        self.mono_to_color_processor = (
            self.mono_to_color_sdk.create_mono_to_color_processor(
                self.camera.camera_sensor_type,
                self.camera.color_filter_array_phase,
                self.camera.get_color_correction_matrix(),
                self.camera.get_default_white_balance_matrix(),
                self.camera.bit_depth,
            )
        )

    def set_color_processor_gains(self, RGB):
        """Sets the RGB gains of the color processor.

        Args:
            RGB (list): List with RGB gains to be set.
        """
        if len(RGB) == 3:
            self.mono_to_color_processor.red_gain = RGB[0]
            self.mono_to_color_processor.green_gain = RGB[1]
            self.mono_to_color_processor.blue_gain = RGB[2]
        else:
            raise ValueError("Input parameter RGB length must be 3")

    def set_color_processor_properties(
        self,
        color_space=COLOR_SPACE.SRGB,
        output_format=FORMAT.RGB_PIXEL,
        verbose=False,
    ):
        """Sets properties of color processor.

        Args:
            color_space (COLOR_SPACE): Color space. Default is COLOR_SPACE.SRGB.
            output_format (FORMAT): Output format. Default is FORMAT.RGB_PIXEL.
            verbose (bool): If True, print information to terminal.
        """
        self.mono_to_color_processor.color_space = color_space
        self.mono_to_color_processor.output_format = output_format
        if verbose:
            print("Color processor properties set to:")
            self.get_color_processor_properties(verbose=True)

    def get_color_processor_gains(self, verbose=False):
        """Gets RGB gains of color processor.

        Args:
            verbose (bool): If True, print information to terminal.

        Returns:
            list: List with RGB gains.
        """
        red_gain = self.mono_to_color_processor.red_gain
        green_gain = self.mono_to_color_processor.green_gain
        blue_gain = self.mono_to_color_processor.blue_gain
        if verbose:
            print(
                f"Color gains: R {red_gain} - G {green_gain} - B {blue_gain}"
            )
        return [red_gain, green_gain, blue_gain]

    def get_color_processor_properties(self, verbose=True):
        """Gets properties of color processor.

        Args:
            verbose (bool): If True, print information to terminal.

        Returns:
            dict: Dictionary with color processor properties.
        """
        keys = ["color_space", "output_format"]
        values = [
            self.mono_to_color_processor.color_space,
            self.mono_to_color_processor.output_format,
        ]
        props = dict(zip(keys, values))  # Dictionary with properties
        if verbose:
            print("Color processor properties:")
            print(list(props.items()))
            self.get_color_processor_gains(verbose=True)
        return props

    # --- Camera configuration functions ---
    def set_image_poll_timeout_ms(self, image_poll_timeout_ms):
        """Sets image poll timeout in milliseconds.

        Args:
            image_poll_timeout_ms (int): Poll timeout in ms.
        """
        try:
            self.camera.image_poll_timeout_ms = image_poll_timeout_ms
        except Exception as error:
            print(
                f"Encountered error: {error}, image poll timeout could not be set to {image_poll_timeout_ms} ms."
            )
            self.dispose()
        if self.verbose:
            print(
                f"Camera image poll timeout has been set to {image_poll_timeout_ms} ms."
            )

    def set_frames_per_trigger_zero_for_unlimited(
        self, frames_per_trigger_zero_for_unlimited
    ):
        """Sets the number of frames generated per software or hardware trigger.

        Args:
            frames_per_trigger_zero_for_unlimited (int): Number of frames per trigger. Set to 0 for unlimited.
        """
        try:
            self.camera.image_poll_timeout_ms = (
                frames_per_trigger_zero_for_unlimited
            )
        except Exception as error:
            print(
                f"Encountered error: {error}, number of frames generated per software or hardware trigger could not be set to {frames_per_trigger_zero_for_unlimited}."
            )
            self.dispose()
        if self.verbose:
            print(
                f"Camera number of frames generated per software or hardware trigger have been set to {frames_per_trigger_zero_for_unlimited}."
            )

    def get_exposure_time(self) -> float:
        """Get exposure time in seconds."""
        if self.simulated:
            return self._simulated_settings.get('exposure_time', 0.1)  # Default simulated exposure time in seconds
        return self.camera.exposure_time_us * 1e-6

    def set_exposure_time(self, value):
        """Sets camera exposure time in seconds.

        Args:
            exposure_time (float): Camera exposure time in seconds.
        """
        if self.simulated:
            self._simulated_settings['exposure_time'] = value
        else:
            self.set_exposure_time_us(value * 1e6)

    def set_exposure_time_us(self, value):
        """Sets camera exposure time in microseconds.

        Args:
            exposure_time_us (int): Camera exposure time in us.
        """
        if self.simulated:
            self._simulated_settings['exposure_time_us'] = value
        else:
            try:
                self.camera.exposure_time_us = value
            except Exception as error:
                print(
                    f"Encountered error: {error}, exposure time us could not be set to {value} us."
                )
                self.dispose()
            if self.verbose:
                print(
                    f"Camera exposure time has been set to {value} us."
                )

    def _get_binning(self):
        """Returns the binning of the camera."""
        if self.simulated:
            return self._simulated_settings.get('binning', microscope.Binning(1, 1))  # Default binning if not set
        h = self.camera.binx
        v = self.camera.biny
        return microscope.Binning(h, v)

    def _set_binning(self, binning: microscope.Binning):
        """Sets the binning of the camera."""
        if self.simulated:
            self._simulated_settings['binning'] = binning
        else:
            self.camera.binx = binning.h
            self.camera.biny = binning.v

    # TODO: replace this with add sedtting
    def set_trigger(self, trigger_mode):
        """set the trigger mode of the camera."""
        # TODO: this probably is not right
        self._trigger_mode = trigger_mode

    @property
    def trigger_mode(self) -> microscope.TriggerMode:
        trigger_string = self._trigger_mode.lower()
        return STRING_TO_TRIGGER[trigger_string][1]

    @property
    def trigger_type(self):
        trigger_string = self._trigger_mode.lower()
        return STRING_TO_TRIGGER[trigger_string][0]

    def _set_roi(self, roi):
        """Sets camera region of interest.

        Args:
            roi (tuple): Region of interest (x, y, width, height).
        """
        if self.simulated:
            self._simulated_settings['roi'] = roi  # Store ROI in simulated settings
            if self.verbose:
                print(f"Simulated camera region of interest has been set to {roi}")
        else:
            try:
                self.camera.roi = roi
                if self.verbose:
                    print(f"Camera region of interest has been set to {roi}")
            except Exception as error:
                print(
                    f"Encountered error: {error}, region of interest could not be set to {roi}."
                )
                self.dispose()

    def _set_gain(self, value):
        """Sets the gain of the camera."""
        if self.simulated:
            self._simulated_settings['gain'] = value  # Store gain in simulated settings
        else:
            self._gain = value

    def _get_roi(self):
        """Gets camera region of interest.

        Returns:
            tuple: Region of interest (x, y, width, height).
        """
        if self.simulated:
            return self._simulated_settings.get('roi', (0, 0, 512, 512))  # Default simulated ROI
        return self.camera.roi

    def set_continuous_mode(self):
        """Sets camera to continuous mode."""
        if self.simulated:
            return
        if self.camera.frames_per_trigger_zero_for_unlimited != 0:
            try:
                self.set_frames_per_trigger_zero_for_unlimited(
                    0
                )  # start camera in continuous mode
                if self.verbose:
                    print(f"Camera set to continuous mode.")
            except Exception as error:
                print(
                    f"Encountered error: {error}, camera could not be set to continuous mode."
                )
                self.dispose()

    def _do_trigger(
        self, exp_time_us=11000, poll_timeout_ms=1000, verbose=False
    ):
        """Initializes camera acquisition with specified parameters."""
        # Increment the trigger
        self._triggered += 1
        if self.simulated:
            return
        if verbose:
            print(f"Initializing {self.camera_name} camera acquisition")
        self.set_exposure_time_us(exp_time_us)  # set exposure in us
        self.set_continuous_mode()  # start camera in continuous mode
        self.set_image_poll_timeout_ms(
            poll_timeout_ms
        )  # 1 second polling timeout
        if not self.camera.is_armed:
            self.camera.arm(2)
        self.camera.issue_software_trigger()
        self.acq_initialized = True
        if verbose:
            print(f"{self.camera_name} camera acquisition initialized")

    # --- Image acquisition functions ---
    def get_frame(self, disarm=False):
        """Gets a frame from the camera.

        Args:
            disarm (bool): If True, disarm the camera after getting the frame.

        Returns:
            Frame: Camera frame object.
        """
        frame = self.camera.get_pending_frame_or_null()
        if frame is not None:
            return frame
        else:
            print("Timeout reached during polling, program exiting...")
        if disarm:
            self.camera.disarm()

    def _fetch_data(self, rescale=False, target_bpp=8):
        # TODO: None of these kwargs will do anything in the new implementation
        """Gets an image from the camera.

        Args:
            rescale (bool): If True, rescale image to target bit depth.
            target_bpp (int): Target bit depth for rescaling.

        Returns:
            Image: PIL Image object.
        """
        if self._acquiring and self._triggered > 0:
            _logger.info("Sending image")
            time.sleep(self.get_cycle_time())
            if self.simulated:
                dark = int(32 * np.random.rand())
                light = int(255 - 128 * np.random.rand())
                width = self.get_roi().width
                height = self.get_roi().height
                image = self._image_generator.get_image(
                    width, height, dark, light, index=self._sent
                )
                self._sent += 1
                self._triggered -= 1
                return image
            frame = self.get_frame()
            if rescale:
                # Bitwise right shift to scale down image
                image = frame.image_buffer >> (
                    self.camera.bit_depth - target_bpp
                )
            else:
                image = frame.image_buffer
            self._sent += 1
            self._triggered -= 1
            # TODO: This needs to check the image format is just an ndarray as expected.
            return image

    def get_raw_color_image(self, transform_key="48", reshape=True):
        """Gets a raw color image from the camera.

        Args:
            transform_key (str): Color transformation key ("48", "32", or "24").
            reshape (bool): If True, reshape the image array.

        Returns:
            np.ndarray: Raw color image data.
        """
        frame = self.get_frame()

        if self.very_verbose:
            print(
                f"Red Gain = {self.mono_to_color_processor.red_gain}\n"
                f"Green Gain = {self.mono_to_color_processor.green_gain}\n"
                f"Blue Gain = {self.mono_to_color_processor.blue_gain}\n"
            )

        if transform_key == "48":
            # Convert to 48-bit RGB image
            colorImage = self.mono_to_color_processor.transform_to_48(
                frame.image_buffer,
                self.camera.image_width_pixels,
                self.camera.image_height_pixels,
            )
            if reshape:
                colorImage = colorImage.reshape(
                    self.camera.image_height_pixels,
                    self.camera.image_width_pixels,
                    3,
                )
        elif transform_key == "32":
            # Convert to 32-bit RGBA image
            colorImage = self.mono_to_color_processor.transform_to_32(
                frame.image_buffer,
                self.camera.image_width_pixels,
                self.camera.image_height_pixels,
            )
            if reshape:
                colorImage = colorImage.reshape(
                    self.camera.image_height_pixels,
                    self.camera.image_width_pixels,
                    4,
                )
        elif transform_key == "24":
            # Convert to 24-bit RGB image
            colorImage = self.mono_to_color_processor.transform_to_24(
                frame.image_buffer,
                self.camera.image_width_pixels,
                self.camera.image_height_pixels,
            )
            if reshape:
                colorImage = colorImage.reshape(
                    self.camera.image_height_pixels,
                    self.camera.image_width_pixels,
                    3,
                )
        else:
            raise ValueError(
                f"{transform_key} is not a valid key for color transformation."
            )

        return colorImage

    def get_color_image(self, transform_key="48"):
        """Gets a color PIL image from the camera.

        Args:
            transform_key (str): Color transformation key ("48", "32", or "24").

        Returns:
            Image: PIL Image object.
        """
        return Image.fromarray(
            self.get_raw_color_image(transform_key), mode="RGB"
        )

    def save_color_image(
        self,
        img_name,
        img_format="png",
        folder_path="",
        color_transformation="48",
        metadata_dict=None,
    ):
        """Saves a color image with optional metadata.

        Args:
            img_name (str): Image file name.
            img_format (str): Image format (e.g., "png").
            folder_path (str): Path to save the image.
            color_transformation (str): Color transformation key ("48", "32", or "24").
            metadata_dict (dict): Dictionary containing metadata to be saved with the image.
        """
        img = self.get_color_image(transform_key=color_transformation)
        if metadata_dict is not None:
            # Convert metadata dictionary to JSON string
            metadata_string = json.dumps(metadata_dict)
            # Create PngInfo object
            metadata = PngImagePlugin.PngInfo()
            # Add metadata
            metadata.add_text("metadata", metadata_string)
            img.save(
                os.path.join(folder_path, f"{img_name}.{img_format}"),
                pnginfo=metadata,
            )
        else:
            img.save(os.path.join(folder_path, f"{img_name}.{img_format}"))
        return img

    def read_color_image(self, img_path):
        """Reads a color image and its metadata.

        Args:
            img_path (str): Path to the image file.

        Returns:
            tuple: (Image, dict) containing the PIL Image object and metadata dictionary.
        """
        # Open the image
        image = Image.open(img_path)
        # Get the metadata
        metadata_string = image.info.get("metadata")
        # If metadata exists, convert it from JSON to a dictionary
        if metadata_string is not None:
            metadata_dict = json.loads(metadata_string)
        else:
            metadata_dict = None
        return image, metadata_dict

"""
ImageAcquisitionThread - Modified from Thorlabs SDK examples

This class derives from threading.Thread and is given a TLCamera instance during initialization. When started, the thread continuously acquires frames from the camera and converts them to PIL Image objects. These are placed in a queue.Queue object that can be retrieved using get_output_queue(). The thread doesn't do any arming or triggering, so users will still need to setup and control the camera from a different thread. Be sure to call stop() when it is time for the thread to stop.
"""


class ImageAcquisitionThread(threading.Thread):
    """
    Continuously acquires frames from a Thorlabs camera and converts them to PIL Images.

    This thread acquires frames from the camera and places them in a queue as PIL Image objects.
    It does not handle camera arming or triggering, which should be controlled from a different thread.

    Attributes:
        _camera (TLCamera): The Thorlabs camera instance.
        _previous_timestamp (int): Timestamp of the previously acquired frame.
        _is_color (bool): Whether the camera is a color camera.
        _mono_to_color_sdk (MonoToColorProcessorSDK): Mono-to-color SDK instance (if color camera).
        _image_width (int): Width of the camera image in pixels.
        _image_height (int): Height of the camera image in pixels.
        _mono_to_color_processor (MonoToColorProcessor): Mono-to-color processor (if color camera).
        _bit_depth (int): Bit depth of the camera sensor.
        _image_queue (queue.Queue): Queue to store acquired PIL Image objects.
        _stop_event (threading.Event): Event to signal thread stopping.

    Args:
        camera_controller (CS165CUCamera): The camera controller instance.

    """

    def __init__(self, camera_controller):
        # type: (TLCamera) -> ImageAcquisitionThread
        super(ImageAcquisitionThread, self).__init__()
        self._camera = camera_controller.camera
        self._previous_timestamp = 0
        # setup color processing if necessary
        if self._camera.camera_sensor_type != SENSOR_TYPE.BAYER:
            # Sensor type is not compatible with the color processing library
            self._is_color = False
        else:
            self._mono_to_color_sdk = camera_controller.mono_to_color_sdk
            self._image_width = self._camera.image_width_pixels
            self._image_height = self._camera.image_height_pixels
            self._mono_to_color_processor = (
                self._mono_to_color_sdk.create_mono_to_color_processor(
                    SENSOR_TYPE.BAYER,
                    self._camera.color_filter_array_phase,
                    self._camera.get_color_correction_matrix(),
                    self._camera.get_default_white_balance_matrix(),
                    self._camera.bit_depth,
                )
            )
            self._is_color = True
        self._bit_depth = camera_controller.camera.bit_depth
        self._camera.image_poll_timeout_ms = (
            0  # Do not want to block for long periods of time
        )
        self._image_queue = queue.Queue(maxsize=2)
        self._stop_event = threading.Event()

    def get_output_queue(self):
        """
        Returns the queue containing acquired PIL Image objects.

        Returns:
            queue.Queue: The image queue.
        """
        return self._image_queue

    def stop(self):
        """
        Stops the image acquisition thread.
        """
        self._stop_event.set()

    def _get_color_image(self, frame):
        """
        Converts a camera frame to a color PIL Image.

        Args:
            frame (Frame): The camera frame to convert.

        Returns:
            Image: The color PIL Image object.
        """
        width = frame.image_buffer.shape[1]
        height = frame.image_buffer.shape[0]
        if (width != self._image_width) or (height != self._image_height):
            self._image_width = width
            self._image_height = height
            print(
                "Image dimension change detected, image acquisition thread was updated"
            )
        # color the image. transform_to_24 will scale to 8 bits per channel
        color_image_data = self._mono_to_color_processor.transform_to_24(
            frame.image_buffer, self._image_width, self._image_height
        )
        color_image_data = color_image_data.reshape(
            self._image_height, self._image_width, 3
        )
        # return PIL Image object
        return Image.fromarray(color_image_data, mode="RGB")

    def _get_image(self, frame):
        """
        Converts a camera frame to a grayscale PIL Image.

        Args:
            frame (Frame): The camera frame to convert.

        Returns:
            Image: The grayscale PIL Image object.
        """
        scaled_image = frame.image_buffer >> (self._bit_depth - 8)
        return Image.fromarray(scaled_image)

    def run(self):
        """
        Continuously acquires and processes camera frames until stopped.
        """
        while not self._stop_event.is_set():
            try:
                frame = self._camera.get_pending_frame_or_null()
                if frame is not None:
                    if self._is_color:
                        pil_image = self._get_color_image(frame)
                else:
                    pil_image = self._get_image(frame)
                self._image_queue.put_nowait(pil_image)
            except queue.Full:
                # No point in keeping this image around when the queue is full, let's skip to the next one
                pass
            except Exception as error:
                print(
                    "Encountered error: {error}, image acquisition will stop.".format(
                        error=error
                    )
                )
                break
        print("Image acquisition has stopped")


class CS165CUBRCamera(CS165CUCamera):
    """
    Raman camera controller for the Thorlabs CS165CU camera.

    This class implements the `BRamanCamera` interface using the `CS165CUCamera` class
    to provide control over the Thorlabs CS165CU Raman camera.

    Attributes:
        config (dict): Configuration dictionary for the camera.
        name (str): The name of the camera.

    Args:
        config (dict): A dictionary containing configuration parameters for the camera.

    """

    def __init__(self, **kwargs):
        # self.config = config
        # self.name = self.config.get("name", "CS165CU")
        # TODO: reinstate configuration
        super().__init__(self, **kwargs)

    def _fetch_data(self, color=True):
        """Acquires a color image from the camera.

        Args:
            color (bool, optional): This argument is ignored as the CS165CU
            camera only captures color images. Defaults to True.

        Returns:
            Image: The acquired PIL Image object.

        """
        if self.simulated:
            # TODO: these fake images can be made a single fixture and with size set by pixel size etc.
            return Image.fromarray(
                np.random.randint(0, 255, (512, 512), dtype=np.uint8)
            )
        return CS165CUCamera.get_color_image(self, transform_key="48")

    def _close(self, force=False, verbose=True):
        """
        Closes the camera, ensuring any necessary cleanup is performed.

        Args:
            force (bool): Forces closure. Defaults to False.
            verbose (bool): If True, enables verbose output during the operation.

        """
        super().dispose(self)

    def _initialize(self, verbose=True):
        """
        Initializes the camera.

        Prepares the camera for operation, if needed.

        Args:
            verbose (bool): If True, enables verbose output during the operation.

        """
        if verbose:
            print(f"Initializing camera {self.name}...")
        super().initialize_acquisition(
            self, exp_time_us=11000, poll_timeout_ms=1000, verbose=True
        )
        if verbose:
            print(f"Camera {self.name} INITIALIZED.")

    def set_gain_dB(self, gain):
        """
        Sets the gain of the camera in dB.

        Args:
            gain (float): The gain value in dB.
        """
        warnings.warn("CSU165 camera cannot gain method not defined!")


if __name__ == "__main__":
    camera = CS165CUCamera(simulated=False)
    print(camera._fetch_data())
