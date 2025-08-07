# Standard Library Imports
import logging 
import time

# Third Party Imports
from gxipy import DeviceManager, Device 
import numpy as np

# Local Imports
#from navigate.model.utils.exceptions import UserVisibleException 

logger = logging.getLogger(__name__)


class MER2_1220_32U3C:
    """
    Interface for Daheng MER2-1220-32U3C USB3 camera using the gxipy SDK.
    """

    def __init__(self, microscope_name, device_connection, configuration, use_threading=False):
        """
        Initialize the camera with given configuration.

        Parameters
        ----------
        microscope_name : str
            Name of the microscope this camera is associated with.
        device_connection : dict
            Connection information for the camera.
        configuration : dict
            Device configuration settings (e.g. resolution, exposure).
        use_threading : bool
            Whether to enable threaded image acquisition.
        """
        pass

        # Store config settings (e.g., trigger mode, exposure time).
        self.configuration = configuration 

        # gxipy.Device object representing the connected camera hardware.
        self.device = None

        # gxipy.FeatureControl object giving access to all camera settings
        self.feature_control = None

        # gxipy.DataStream object managing image buffer queueing and retrieval.
        self.data_stream = None

        # Unique serial number string of the connected camera.
        self.device_serial_number = None
        
        # Integer size in bytes of each image buffer (used for buffer registration).
        self.payload_size = None

        # Boolean flag indicating whether the camera is currently connected.
        self.is_connected = False

    def __str__(self):
        status = "Connected" if self.is_connected else "Disconnected"
        serial = self.device_serial_number if self.device_serial_number else "N/A"
        return f"MER2_1220_32U3C Camera [Serial: {serial}, Status: {status}]"

    def connect(self):
        """
        Establish connection to the Daheng camera and initialize the SDK device.
        """
        # Update device list
        device_manager = DeviceManager()
        device_manager.update_device_list()
        dev_info_list = device_manager.get_device_list()

        if not dev_info_list:
            raise RuntimeError("No Daheng camera found. Please check USB connection.")

        # Open the first available device (indexing starts from 1)
        self.device = device_manager.open_device_by_index(1)

        # Access the feature control interface (string-based _s version)
        self.feature_control = self.device.get_remote_device_feature_control()
        self.data_stream = self.device.data_stream

        # Read camera metadata
        self.device_serial_number = self.feature_control.get_string_feature("DeviceSerialNumber").get()
        self.payload_size = self.feature_control.get_int_feature("PayloadSize").get()

        # Set acquisition mode to Continuous
        self.feature_control.get_enum_feature("AcquisitionMode").set("Continuous")

        self.is_connected = True

    @property
    def serial_number(self):
        """
        Return the serial number of the connected camera.

        Returns
        -------
        str
            Serial number of the camera.

        Raises
        ------
        RuntimeError
            If the camera is not connected.
        """
        if not self.is_connected or self.device_serial_number is None:
            raise RuntimeError("Camera must be connected to retrieve serial number.")
        return self.device_serial_number    

    def disconnect(self):
        """
        Close the connection to the camera and release resources.
        """
        if self.device is not None:
            try:
                self.device.close_device()
            except Exception as e:
                logger.warning(f"Warning: Error while closing device: {e}")
            finally:
                self.device = None

        # Reset all dependent attributes
        self.feature_control = None
        self.data_stream = None
        self.device_serial_number = None
        self.payload_size = None
        self.is_connected = False

        logging.info("Camera disconnected.")

    def set_exposure_time(self, exposure_time: float):
        """
        Set camera exposure time in seconds.
        Note: gxipy uses microseconds internally.
        """
        if not self.is_connected:
            raise RuntimeError("Camera must be connected to set exposure time.")
        
        exposure_time_us = int(exposure_time * 1_000_000)
        self.feature_control.get_float_feature("ExposureTime").set(exposure_time_us)
        logger.info(f"Exposure time set to {exposure_time_us} µs")


    def set_gain(self, gain: float):
        """
        Set analog gain in dB (depends on camera model).
        """
        if not self.is_connected:
            raise RuntimeError("Camera must be connected to set gain.")
        
        self.feature_control.get_float_feature("Gain").set(gain)
        logger.info(f"Gain set to {gain} dB")


    def set_binning(self, binning_x: int, binning_y: int):
        """
        Set horizontal and vertical binning.
        """
        if not self.is_connected:
            raise RuntimeError("Camera must be connected to set binning.")

        self.feature_control.get_int_feature("BinningHorizontal").set(binning_x)
        self.feature_control.get_int_feature("BinningVertical").set(binning_y)
        logger.info(f"Binning set to {binning_x}x{binning_y}")


    def set_ROI(self, offset_x: int, offset_y: int, width: int, height: int):
        """
        Set region of interest (ROI) for the image sensor.
        """
        if not self.is_connected:
            raise RuntimeError("Camera must be connected to set ROI.")

        self.feature_control.get_int_feature("OffsetX").set(offset_x)
        self.feature_control.get_int_feature("OffsetY").set(offset_y)
        self.feature_control.get_int_feature("Width").set(width)
        self.feature_control.get_int_feature("Height").set(height)
        logger.info(f"ROI set to (x={offset_x}, y={offset_y}, w={width}, h={height})")

    def set_trigger_mode(self, mode: str):
        """
        Set camera trigger mode to 'ON' or 'OFF'.

        Parameters
        ----------
        mode : str
            Must be a valid enum entry for the TriggerMode feature - typically 'ON' or 'OFF'.

        Notes
        -----
        Enum values are case-sensitive. This camera expects uppercase values as defined
        in GxSwitchEntry (e.g., 'ON', 'OFF').

        If this fails due to an unknown enum value, verify supported entries by calling:
            self.feature_control.get_enum_feature("TriggerMode").get_entry_list()
        """
        if not self.is_connected:
            raise RuntimeError("Camera must be connected to set trigger mode.")

        self.feature_control.get_enum_feature("TriggerMode").set(mode)
        logger.info(f"Trigger mode set to {mode}")


    def set_trigger_source(self, source: str):
        """
        Set the trigger source (e.g., 'LINE1', 'SOFTWARE').

        Parameters
        ----------
        source : str
            Must be one of: 'SOFTWARE', 'LINE0', 'LINE1', 'LINE2', 'LINE3'.
            These must be uppercase, as required by the GxTriggerSourceEntry enum.

        Notes
        -----
        If this fails due to an unknown enum value, check valid options using:
            self.feature_control.get_enum_feature("TriggerSource").get_entry_list()
        """
        if not self.is_connected:
            raise RuntimeError("Camera must be connected to set trigger source.")

        self.feature_control.get_enum_feature("TriggerSource").set(source)
        logger.info(f"Trigger source set to {source}")

    def send_software_trigger(self):
        """
        Send a software trigger to the camera.

        Raises
        ------
        RuntimeError
            If trigger mode or source is misconfigured, or camera not connected.
        """
        if not self.is_connected:
            raise RuntimeError("Camera must be connected to send a software trigger.")

        try:
            self.feature_control.get_command_feature("TriggerSoftware").send_command()
            logger.debug("Software trigger sent.")
        except Exception as e:
            raise RuntimeError(
                "Failed to send software trigger. Make sure:\n"
                "- Trigger mode is set to 'ON'\n"
                "- Trigger source is set to 'SOFTWARE'\n"
                f"Original error: {e}"
            )

    def start_acquisition(self):
        """
        Start image acquisition on the camera.
        """
        if not self.is_connected:
            raise RuntimeError("Camera must be connected before starting acquisition.")

        try:
            self.data_stream.start_stream()
            self.feature_control.get_command_feature("AcquisitionStart").send_command()
            
            # Get current acquisition and trigger settings
            acq_mode = self.feature_control.get_enum_feature("AcquisitionMode").get_current_entry().get_symbolic()
            trigger_mode = self.feature_control.get_enum_feature("TriggerMode").get_current_entry().get_symbolic()
            trigger_source = self.feature_control.get_enum_feature("TriggerSource").get_current_entry().get_symbolic()

            logger.info(
                f"Acquisition started: "
                f"AcquisitionMode={acq_mode}, "
                f"TriggerMode={trigger_mode}, "
                f"TriggerSource={trigger_source}"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to start acquisition: {e}")

    def stop_acquisition(self):
        """
        Stop image acquisition and flush camera buffers.
        """
        if not self.is_connected:
            raise RuntimeError("Camera must be connected to stop acquisition.")

        try:
            self.feature_control.get_command_feature("AcquisitionStop").send_command()
            self.data_stream.stop_stream()
            logger.info("Acquisition stopped.")
        except Exception as e:
            raise RuntimeError(f"Failed to stop acquisition: {e}")


    def snap_software_triggered(self, timeout_ms=1000):
        """
        Sends a software trigger and retrieves the resulting image.

        This should be used when:
        - TriggerMode is ON
        - TriggerSource is SOFTWARE

        Raises RuntimeError if misconfigured.
        """
        if not self.is_connected:
            raise RuntimeError("Camera not connected.")

        # Optional: Check trigger config strictly
        trigger_mode = self.feature_control.get_enum_feature("TriggerMode").get_current_entry().get_symbolic()
        trigger_source = self.feature_control.get_enum_feature("TriggerSource").get_current_entry().get_symbolic()

        if not (trigger_mode == "ON" and trigger_source == "SOFTWARE"):
            raise RuntimeError("snap_software_triggered() requires TriggerMode=ON and TriggerSource=SOFTWARE.")

        self.send_software_trigger()
        
        return self.get_image(timeout_ms=timeout_ms)

    def get_image(self, timeout_ms=1000, return_raw=False):
        """
        Retrieve the next acquired image from the camera buffer.

        Parameters
        ----------
        timeout_ms : int
            How long to wait for an image (in milliseconds).
        return_raw : bool
            If True, returns the raw gxipy image object.
            If False (default), returns a NumPy array.

        Returns
        -------
        np.ndarray or gxipy.RawImage
            Acquired image.

        Raises
        ------
        RuntimeError
            If image acquisition fails or times out.
        """
        if not self.is_connected:
            raise RuntimeError("Camera must be connected to retrieve images.")

        try:
            raw_image = self.data_stream.get_image(timeout_ms) # Note that this is called on the data_stream_object 
            if raw_image is None:
                raise RuntimeError("No image received from camera.")

            return raw_image if return_raw else raw_image.get_numpy_array()

        except Exception as e:
            raise RuntimeError(f"Error retrieving image: {e}")
        
    