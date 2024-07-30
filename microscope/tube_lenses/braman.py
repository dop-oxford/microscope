"""BRamanTubeLens Class."""
import pandas as pd
import os

configurations = {
    'WFA4100': {
        'Maker': 'Thorlabs',
        'Magnification': '1',
        'Focal_Length': '200',
    },
}


class BRamanTubeLens:
    def __init__(
        self, name, maker=None, magnification=None, focal_length=None
    ):
        self._name = name
        self._magnification = magnification
        self._maker = maker
        self._focal_length = focal_length  # Tube lens focal distance in mm
        self.set_tube_lens_from_name(self._name)
        self._metadata = self.set_metadata()

    def set_tube_lens_from_name(self, name):
        config = configurations[name]
        self._magnification = float(config['Magnification'])
        self._maker = config['Maker']
        # Tube lens focal distance in mm
        self._focal_length = float(config['Focal_Length'])

    def set_metadata(self):
        """
        Constructs and returns a metadata dictionary for the tube lens.

        Returns:
            dict: A dictionary containing metadata about the tube lens,
            including its name, maker, magnification, and focal length.
        """
        metadata = dict(
            Tube_Lens=self._name,
            Tube_Lens_Maker=self._maker,
            Tube_Lens_Magnification=self._magnification,
            Tube_Lens_Focal_Length=self._focal_length
        )
        self._metadata = metadata
        return metadata

    def get_metadata(self):
        """
        Retrieves the metadata dictionary for the tube lens.

        Returns:
            dict: A dictionary containing the tube lens's metadata, including
            its name, maker, magnification, and focal length.
        """
        return self._metadata

    def get_name(self):
        """
        Retrieves the name of the tube lens.

        Returns:
            str: The name of the tube lens.
        """
        return self._name

    def set_name(self, name):
        """
        Sets the name of the tube lens.

        Args:
            name (str): The new name for the tube lens.
        """
        self._name = name

    def get_magnification(self):
        """
        Retrieves the magnification factor of the tube lens.

        Returns:
            float: The magnification factor of the tube lens.
        """
        return self._magnification

    def set_magnification(self, magnification):
        """
        Sets the magnification factor of the tube lens.

        Args:
            magnification (float): The new magnification factor for the tube
            lens.
        """
        self._magnification = magnification

    def get_maker(self):
        """
        Retrieves the manufacturer of the tube lens.

        Returns:
            str: The manufacturer of the tube lens.
        """
        return self._maker

    def set_maker(self, maker):
        """
        Sets the manufacturer of the tube lens.

        Args:
            maker (str): The new manufacturer for the tube lens.
        """
        self._maker = maker

    def get_focal_length(self):
        """
        Retrieves the focal length of the tube lens.

        Returns:
            float: The focal length of the tube lens in millimeters.
        """
        return self._focal_length

    def set_focal_length(self, focal_length):
        """
        Sets the focal length of the tube lens.

        Args:
            focal_length (float): The new focal length for the tube lens, in
            millimeters.
        """
        self._focal_length = focal_length


if __name__ == '__main__':
    tube_lens = BRamanTubeLens('WFA4100')
    print(tube_lens.get_metadata())
