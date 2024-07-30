from abc import ABC, abstractmethod
import os

class BRamanSpectrometer(ABC):
    def __init__(self, config):
        self.config = config
        self.name = self.config.get('name', 'Spectrometer')
    
    @abstractmethod
    def print_info(self):
        """
        Prints information about the spectrometer.
        """
        pass
    
    @abstractmethod
    def _initialize(self, verbose=True):
        """
        Initializes the spectrometer.

        Prepares the spectrometer for operation, if needed.
        
        """
        pass 

    @abstractmethod
    def _close(self, force=False, verbose=True):
        """
        Closes the spectrometer, ensuring any necessary cleanup is performed.

        This method should be implemented by subclasses to close connections, release resources, or perform other cleanup actions specific to the controller.
        """
        pass

    @abstractmethod
    def get_current_temperature():
        pass

    @abstractmethod
    def get_spectrum_df(self):
        pass

    @abstractmethod
    def get_metadata(self):
        pass

    def initialize(self, force=False, verbose=True):
        """
        Initializes the spectrometer.

        Prepares the spectrometer for operation, if needed.
        
        Args:
            force (bool): Forces initialization (no impact in this case as nothing to force).
            verbose (bool): If True, enables verbose output during the operation.

        """
        if verbose:
            print(f"Initializing spectrometer {self.name}...")
        self._initialize(verbose=verbose)
        if verbose:
            print(f"Spectrometer {self.name} INITIALIZED.")

    def close(self, force=False, verbose=True):
        """
        Closes the spectrometer, ensuring any necessary cleanup is performed.

        This method should be implemented by subclasses to close connections, release resources, or perform other cleanup actions specific to the controller.
        """
        if verbose:
            print(f"Closing spectrometer {self.name}...")
        self._close(force, verbose)
        if verbose:
            print(f"Spectrometer {self.name} CLOSED.")
        pass


