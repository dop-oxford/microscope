import warnings
import microscope.abc

import warnings
import sys
import os
from pathlib import Path

from microscope.cameras._thorlabs.tl_camera import TLCameraSDK, TLCamera, Frame, OPERATION_MODE, ROI
from microscope.cameras._thorlabs.tl_camera_enums import SENSOR_TYPE
from microscope.cameras._thorlabs.tl_mono_to_color_processor import MonoToColorProcessorSDK
from microscope.cameras._thorlabs.tl_mono_to_color_enums import COLOR_SPACE
from microscope.cameras._thorlabs.tl_color_enums import FORMAT
import numpy as np
import os
import json
import tkinter as tk
from PIL import Image, ImageTk, PngImagePlugin
import typing
import threading
import queue
import matplotlib.pyplot as pl

class CS165CUCamera(microscope.abc.Camera):
    """
    Class to control the Thorlabs CS165CU Camera

    Attributes:
        verbose (bool): If True, info is printed in terminal
        very_verbose (bool): If True, more info is printed in terminal
        sdk (TLCameraSDK): SDK instance
        camera_name (str): Name of camera
        camera_list (list): List of available cameras
        camera (TLCamera): Camera instance
        _is_color (bool): Whether the camera is color
        mono_to_color_sdk (MonoToColorProcessorSDK): Mono to color SDK instance (if camera is color)
        mono_to_color_processor (MonoToColorProcessor): Mono to color processor instance (if camera is color)
        acq_initialized (bool): Whether acquisition has been initialized
        metadata (dict): Camera metadata

    Methods:
        print_info(): Prints camera information to terminal
        dispose(): Cleans up SDK and camera resources
        rename_camera(camera_name): Renames the camera
        get_sensor_pixel_size(): Returns sensor dimensions in pixels
        get_pixel_size(): Returns pixel dimensions in um
        get_sensor_size_um(): Returns sensor dimensions in um
        set_metadata(): Sets camera metadata
        get_metadata(): Returns camera metadata
        initialize_mono_to_color_processor(): Initializes mono to color processor (if camera is color)
        set_color_processor_gains(RGB): Sets color processor RGB gains
        set_color_processor_properties(color_space, output_format, verbose): Sets color processor properties
        get_color_processor_gains(verbose): Gets color processor RGB gains
        get_color_processor_properties(verbose): Gets color processor properties
        set_image_poll_timeout_ms(image_poll_timeout_ms): Sets image poll timeout in ms
        set_frames_per_trigger_zero_for_unlimited(frames_per_trigger_zero_for_unlimited): Sets frames per trigger
        set_exposure_time_us(exposure_time_us): Sets camera exposure time in microseconds
        set_roi(roi): Sets camera region of interest
        get_roi(): Gets camera region of interest
        set_continuous_mode(): Sets camera to continuous mode
        initialize_acquisition(exp_time_us, poll_timeout_ms, verbose): Initializes camera acquisition
        get_frame(disarm): Gets a frame from the camera
        get_image(rescale, target_bpp): Gets an image from the camera
        get_raw_color_image(transform_key, reshape): Gets a raw color image from the camera
        get_color_image(transform_key): Gets a color PIL image from the camera
        save_color_image(img_name, img_format, folder_path, color_transformation, metadata_dict): Saves a color image
        read_color_image(img_path): Reads a color image and its metadata
        get_camera(): Returns camera instance
        get_camera_list(): Returns list of available cameras
        get_sdk(): Returns SDK instance
        get_camera_name(): Returns camera name
        get_mono_to_color_processor(): Returns mono to color processor instance (if camera is color)
        get_mono_to_color_sdk(): Returns mono to color SDK instance (if camera is color)
        live_image(root, dispose): Starts live image view
        camera_GUI(root, dispose): Starts camera GUI

    """
    def __init__(self,
                 camera_number=None,  # The number in the list of cameras of the camera we want to get
                 camera_name=None,  # Name of camera
                 ini_acq=False,  # Whether to initialize the acquisition with the default values
                 verbose=True,  # If True, info in printed in terminal
                 very_verbose=False,
                 simulated=False):  # If True, more info in printed in terminal
        super().__init__()
        self.add_setting("example_setting", "str", lambda x: None, lambda x: None, lambda x: x)
        # TODO: this obviously needs a proper solution:
        os.add_dll_directory("C:\Program Files\Thorlabs\Scientific Imaging\ThorCam")
        if simulated:
            self.simulated = True
        self._is_color = False # TODO: This is a hack that needs removed later.
        self.verbose = verbose
        self.very_verbose = very_verbose
        self.camera_name = camera_name
        try: # TODO: This is a hack that needs removed later.
            self.sdk = TLCameraSDK()
            self.camera_list = self.sdk.discover_available_cameras()
        except:
            self.sdk = {}
            self.camera_list = None

        if not self.camera_list:
            self.simulated = True
            self.camera = {}
            warnings.warn("No cameras have been found")
            return

        if camera_number:
            self.camera = self.sdk.open_camera(self.camera_list[camera_number])
        else:
            if len(self.camera_list) == 1:
                self.camera = self.sdk.open_camera(self.camera_list[0])
            else:
                # Select camera from list
                print(self.camera_list)
                try:
                    user_input = int(input(f"Enter integer of the camera that needs to be selected: "))
                    if 0 <= user_input <= len(self.camera_list) - 1:
                        self.camera = self.sdk.open_camera(self.camera_list[user_input])
                    else:
                        print(f"Input should be an integer between 0 and {len(self.camera_list) - 1}. Try again.")
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

        if self.very_verbose:
            self.print_info()

    def _do_shutdown(self):
        """Cleans up the TLCameraSDK and TLCamera instances."""
        if self.simulated:
            return
        if self._is_color:
            try:
                self.mono_to_color_processor.dispose()
            except Exception as exception:
                print(f"Unable to dispose Mono to Color processor: {exception}")
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
    
    def abort():
        """Aborts the camera acquisition."""
        # TODO: work out how to do this.
        pass

    def rename_camera(self, camera_name):
        """Renames the camera.

        Args:
            camera_name (str): New name for the camera.
        """
        try:
            self.camera.name = camera_name
        except Exception as error:
            print(f"Encountered error: {error}, camera name could not be set to {camera_name}.")
            self.dispose()
        if self.verbose:
            print(f"Camera name has been set to {camera_name}.")

    # NOTE: This has been renamed from get_sensor_pixel_size
    def _get_sensor_shape(self):
        """Returns sensor dimensions in pixels.

        Returns:
            list: Sensor dimensions [height, width] in pixels.
        """
        return [self.camera.image_height_pixels, self.camera.image_width_pixels]

    def get_pixel_size(self):
        """Returns pixel dimensions in um.

        Returns:
            list: Pixel dimensions [height, width] in um.
        """
        return [self.camera.sensor_pixel_height_um, self.camera.sensor_pixel_width_um]

    def get_sensor_size_um(self):
        """Returns sensor dimensions in um.

        Returns:
            list: Sensor dimensions [height, width] in um.
        """
        return (np.array(self.get_sensor_pixel_size()) * np.array(self.get_pixel_size())).tolist()

    def set_metadata(self):
        """Sets camera metadata."""
        self.metadata = dict(Camera_Sensor_Size_HxW=self.get_sensor_pixel_size(),
                             Camera_Pixel_Size_HxW=self.get_pixel_size())

    def get_metadata(self):
        """Returns camera metadata.

        Returns:
            dict: Camera metadata dictionary.
        """
        return self.metadata

    # --- Color processing functions ---
    def initialize_mono_to_color_processor(self):
        """Initializes mono to color processor if the camera is color."""
        if not hasattr(self, 'mono_to_color_processor'):
            setattr(self, 'mono_to_color_processor', None)
        self.mono_to_color_processor = self.mono_to_color_sdk.create_mono_to_color_processor(
            self.camera.camera_sensor_type,
            self.camera.color_filter_array_phase,
            self.camera.get_color_correction_matrix(),
            self.camera.get_default_white_balance_matrix(),
            self.camera.bit_depth)

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

    def set_color_processor_properties(self, color_space=COLOR_SPACE.SRGB, output_format=FORMAT.RGB_PIXEL, verbose=False):
        """Sets properties of color processor.

        Args:
            color_space (COLOR_SPACE): Color space. Default is COLOR_SPACE.SRGB.
            output_format (FORMAT): Output format. Default is FORMAT.RGB_PIXEL.
            verbose (bool): If True, print information to terminal.
        """
        self.mono_to_color_processor.color_space = color_space
        self.mono_to_color_processor.output_format = output_format
        if verbose:
            print('Color processor properties set to:')
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
            print(f'Color gains: R {red_gain} - G {green_gain} - B {blue_gain}')
        return [red_gain, green_gain, blue_gain]

    def get_color_processor_properties(self, verbose=True):
        """Gets properties of color processor.

        Args:
            verbose (bool): If True, print information to terminal.

        Returns:
            dict: Dictionary with color processor properties.
        """
        keys = ['color_space', 'output_format']
        values = [self.mono_to_color_processor.color_space,
                  self.mono_to_color_processor.output_format]
        props = dict(zip(keys, values))  # Dictionary with properties
        if verbose:
            print('Color processor properties:')
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
            print(f"Encountered error: {error}, image poll timeout could not be set to {image_poll_timeout_ms} ms.")
            self.dispose()
        if self.verbose:
            print(f"Camera image poll timeout has been set to {image_poll_timeout_ms} ms.")

    def set_frames_per_trigger_zero_for_unlimited(self, frames_per_trigger_zero_for_unlimited):
        """Sets the number of frames generated per software or hardware trigger.

        Args:
            frames_per_trigger_zero_for_unlimited (int): Number of frames per trigger. Set to 0 for unlimited.
        """
        try:
            self.camera.image_poll_timeout_ms = frames_per_trigger_zero_for_unlimited
        except Exception as error:
            print(
                f"Encountered error: {error}, number of frames generated per software or hardware trigger could not be set to {frames_per_trigger_zero_for_unlimited}."
            )
            self.dispose()
        if self.verbose:
            print(
                f"Camera number of frames generated per software or hardware trigger have been set to {frames_per_trigger_zero_for_unlimited}."
            )

    def set_exposure_time(self, exposure_time):
        """Sets camera exposure time in seconds.

        Args:
            exposure_time (float): Camera exposure time in seconds.
        """
        self.set_exposure_time_us(exposure_time * 1e6)

    def set_exposure_time_us(self, exposure_time_us):
        """Sets camera exposure time in microseconds.

        Args:
            exposure_time_us (int): Camera exposure time in us.
        """
        try:
            self.camera.exposure_time_us = exposure_time_us
        except Exception as error:
            print(f"Encountered error: {error}, exposure time us could not be set to {exposure_time_us} us.")
            self.dispose()
        if self.verbose:
            print(f"Camera exposure time has been set to {exposure_time_us} us.")
    
    def _get_binning(self):
        """Returns the binning of the camera."""
        # TODO: implement this using get_binx / biny from the SDK.
        return
    
    def _set_binning(self):
        """Returns the binning of the camera."""
        # TODO: implement this using binx / biny setter from the SDK.
        return
    def set_trigger(self, trigger_mode):
        """set the trigger mode of the camera."""
        # TODO: I think this might be called operation mode on the tlcamera
        pass
    def trigger_mode(self):
        pass
    def trigger_type(self):
        pass

    def _set_roi(self, roi):
        """Sets camera region of interest.

        Args:
            roi (tuple): Region of interest (x, y, width, height).
        """
        try:
            self.camera.roi = roi
            if self.verbose:
                print(f"Camera region of interest has been set to {roi}")
        except Exception as error:
            print(f"Encountered error: {error}, region of interest could not be set to {roi}.")
            self.dispose()

    def _get_roi(self):
        """Gets camera region of interest.

        Returns:
            tuple: Region of interest (x, y, width, height).
        """
        return self.camera.roi

    def set_continuous_mode(self):
        """Sets camera to continuous mode."""
        if self.camera.frames_per_trigger_zero_for_unlimited != 0:
            try:
                self.set_frames_per_trigger_zero_for_unlimited(0)  # start camera in continuous mode
                if self.verbose:
                    print(f"Camera set to continuous mode.")
            except Exception as error:
                print(f"Encountered error: {error}, camera could not be set to continuous mode.")
                self.dispose()

    def _do_trigger(self, exp_time_us=11000, poll_timeout_ms=1000, verbose=False):
        """Initializes camera acquisition with specified parameters."""
        if verbose:
            print(f"Initializing {self.camera_name} camera acquisition")
        self.set_exposure_time_us(exp_time_us)  # set exposure in us
        self.set_continuous_mode()  # start camera in continuous mode
        self.set_image_poll_timeout_ms(poll_timeout_ms)  # 1 second polling timeout
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
        """Gets an image from the camera.

        Args:
            rescale (bool): If True, rescale image to target bit depth.
            target_bpp (int): Target bit depth for rescaling.

        Returns:
            Image: PIL Image object.
        """
        if self.simulated:
            return Image.fromarray(np.random.randint(0, 255, (512, 512), dtype=np.uint8))
        frame = self.get_frame()
        if rescale:
            # Bitwise right shift to scale down image
            image = frame.image_buffer >> (self.camera.bit_depth - target_bpp)
        else:
            image = frame.image_buffer
        return Image.fromarray(image)

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
            print(f"Red Gain = {self.mono_to_color_processor.red_gain}\n"
                  f"Green Gain = {self.mono_to_color_processor.green_gain}\n"
                  f"Blue Gain = {self.mono_to_color_processor.blue_gain}\n")

        if transform_key == "48":
            # Convert to 48-bit RGB image
            colorImage = self.mono_to_color_processor.transform_to_48(frame.image_buffer, self.camera.image_width_pixels,
                                                                     self.camera.image_height_pixels)
            if reshape:
                colorImage = colorImage.reshape(self.camera.image_height_pixels, self.camera.image_width_pixels, 3)
        elif transform_key == "32":
            # Convert to 32-bit RGBA image
            colorImage = self.mono_to_color_processor.transform_to_32(frame.image_buffer, self.camera.image_width_pixels,
                                                                     self.camera.image_height_pixels)
            if reshape:
                colorImage = colorImage.reshape(self.camera.image_height_pixels, self.camera.image_width_pixels, 4)
        elif transform_key == "24":
            # Convert to 24-bit RGB image
            colorImage = self.mono_to_color_processor.transform_to_24(frame.image_buffer, self.camera.image_width_pixels,
                                                                     self.camera.image_height_pixels)
            if reshape:
                colorImage = colorImage.reshape(self.camera.image_height_pixels, self.camera.image_width_pixels, 3)
        else:
            raise ValueError(f"{transform_key} is not a valid key for color transformation.")

        return colorImage

    def get_color_image(self, transform_key="48"):
        """Gets a color PIL image from the camera.

        Args:
            transform_key (str): Color transformation key ("48", "32", or "24").

        Returns:
            Image: PIL Image object.
        """
        return Image.fromarray(self.get_raw_color_image(transform_key), mode='RGB')

    def save_color_image(self, img_name, img_format='png', folder_path='', color_transformation='48',
                         metadata_dict=None):
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
            metadata.add_text('metadata', metadata_string)
            img.save(os.path.join(folder_path, f'{img_name}.{img_format}'), pnginfo=metadata)
        else:
            img.save(os.path.join(folder_path, f'{img_name}.{img_format}'))
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
        metadata_string = image.info.get('metadata')
        # If metadata exists, convert it from JSON to a dictionary
        if metadata_string is not None:
            metadata_dict = json.loads(metadata_string)
        else:
            metadata_dict = None
        return image, metadata_dict

    # --- Getter functions ---
    def get_camera(self):
        """Returns the camera instance.

        Returns:
            TLCamera: Camera instance.
        """
        return self.camera

    def get_camera_list(self):
        """Returns the list of available cameras.

        Returns:
            list: List of available camera names.
        """
        return self.camera_list

    def get_sdk(self):
        """Returns the SDK instance.

        Returns:
            TLCameraSDK: SDK instance.
        """
        return self.sdk

    def get_camera_name(self):
        """Returns the camera name.

        Returns:
            str: Camera name.
        """
        return self.camera_name

    def get_mono_to_color_processor(self):
        """Returns the mono to color processor instance if the camera is color.

        Returns:
            MonoToColorProcessor: Mono to color processor instance.
        """
        return self.mono_to_color_processor

    def get_mono_to_color_sdk(self):
        """Returns the mono to color SDK instance if the camera is color.

        Returns:
            MonoToColorProcessorSDK: Mono to color SDK instance.
        """
        return self.mono_to_color_sdk


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
            self._mono_to_color_processor = self._mono_to_color_sdk.create_mono_to_color_processor(
                SENSOR_TYPE.BAYER,
                self._camera.color_filter_array_phase,
                self._camera.get_color_correction_matrix(),
                self._camera.get_default_white_balance_matrix(),
                self._camera.bit_depth
            )
            self._is_color = True
        self._bit_depth = camera_controller.camera.bit_depth
        self._camera.image_poll_timeout_ms = 0  # Do not want to block for long periods of time
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
            print("Image dimension change detected, image acquisition thread was updated")
        # color the image. transform_to_24 will scale to 8 bits per channel
        color_image_data = self._mono_to_color_processor.transform_to_24(frame.image_buffer,
                                                                         self._image_width,
                                                                         self._image_height)
        color_image_data = color_image_data.reshape(self._image_height, self._image_width, 3)
        # return PIL Image object
        return Image.fromarray(color_image_data, mode='RGB')

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
                print("Encountered error: {error}, image acquisition will stop.".format(error=error))
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

    def __init__(self, config):
        #self.config = config
        #self.name = self.config.get("name", "CS165CU")
        super().__init__(self, config)
        camera_number = self.config.get("camera_number", None)
        ini_acq = self.config.get("ini_acq", False)
        verbose = self.config.get("verbose", False)
        very_verbose = self.config.get("very_verbose", False)
        CS165CUCamera.__init__(self, camera_number=camera_number, ini_acq=ini_acq, 
                               verbose=verbose, very_verbose=very_verbose)

    def _fetch_data(self, color=True):
        """Acquires a color image from the camera. 

        Args:
            color (bool, optional): This argument is ignored as the CS165CU 
            camera only captures color images. Defaults to True.

        Returns:
            Image: The acquired PIL Image object. 

        """
        return CS165CUCamera.get_color_image(self, transform_key="48") 

    def _close(self, force= False, verbose=True): 
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
        super().initialize_acquisition(self, exp_time_us=11000, poll_timeout_ms=1000, verbose=True)
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
    camera = CS165CUCamera(simulated=True)
    print(camera._fetch_data())