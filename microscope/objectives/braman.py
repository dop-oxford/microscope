"""BRamanObjective Class."""
import pandas as pd
import os

configurations = {
    'N PLAN 10x/0.25': {
        'Maker': 'LEICA',
        'Magnification': '10',
        'NA': '0.25',
        'WD': '5.8',
        'Immersion': 'Air',
        'Spot_Size': '80',
        'Tube_Lens_Design': '200',
    },
    'N PLAN 10x/0.25_2': {
        'Maker': 'LEICA',
        'Magnification': '10',
        'NA': '0.25',
        'WD': '17.7',
        'Immersion': 'Air',
        'Spot_Size': '',
        'Tube_Lens_Design': '200',
    },
}


class BRamanObjective:
    def __init__(
        self, name, maker=None, magnification=None, NA=None, WD=None,
        immersion=None, f_tube_lens_design=None
    ):
        self._name = name
        self._magnification = magnification
        self._maker = maker
        # Working distance in mm
        self._WD = WD
        self._NA = NA
        # Design Tube lens focal distance in mm
        self._f_tube_lens_design = f_tube_lens_design
        self._immersion = immersion
        self.set_objective_from_name(self._name)
        self._metadata = self.set_metadata()

    def set_objective_from_name(self, name):
        config = configurations[name]
        self._magnification = float(config['Magnification'])
        self._NA = float(config['NA'])
        self._maker = config['Maker']
        # Working distance in mm
        self._WD = float(config['WD'])
        # Design tube lens focal distance in mm
        self._f_tube_lens_design = float(config['Tube_Lens_Design'])
        self._immersion = config['Immersion']

    def set_metadata(self):
        # Implementation for setting metadata
        metadata = dict(
            Objective=self._name,
            Objective_Maker=self._maker,
            Objective_Magnification=self._magnification,
            Objective_NA=self._NA,
            Objective_WD=self._WD,
            Objective_Immersion=self._immersion,
            Objective_Tube_Lens_f=self._f_tube_lens_design
        )
        self._metadata = metadata
        return metadata

    def get_metadata(self):
        """
        Retrieves the metadata dictionary for the objective.

        Returns:
            dict: A dictionary containing the objective's metadata.
        """
        return self._metadata

    def get_name(self):
        """
        Retrieves the name of the objective.

        Returns:
            str: The name of the objective.
        """
        return self._name

    def set_name(self, name):
        """
        Sets the name of the objective.

        Args:
            name (str): The new name for the objective.
        """
        self._name = name

    def get_magnification(self):
        """
        Retrieves the magnification factor of the objective.

        Returns:
            float: The magnification factor of the objective.
        """
        return self._magnification

    def set_magnification(self, magnification):
        """
        Sets the magnification factor of the objective.

        Args:
            magnification (float): The new magnification factor for the
            objective.
        """
        self._magnification = magnification

    def get_maker(self):
        """
        Retrieves the manufacturer of the objective.

        Returns:
            str: The manufacturer of the objective.
        """
        return self._maker

    def set_maker(self, maker):
        """
        Sets the manufacturer of the objective.

        Args:
            maker (str): The new manufacturer for the objective.
        """
        self._maker = maker

    def get_NA(self):
        """
        Retrieves the numerical aperture (NA) of the objective.

        Returns:
            float: The numerical aperture of the objective.
        """
        return self._NA

    def set_NA(self, NA):
        """
        Sets the numerical aperture (NA) of the objective.

        Args:
            NA (float): The new numerical aperture for the objective.
        """
        self._NA = NA

    def get_WD(self):
        """
        Retrieves the working distance (WD) of the objective in millimeters.

        Returns:
            float: The working distance of the objective.
        """
        return self._WD

    def set_WD(self, WD):
        """
        Sets the working distance (WD) of the objective.

        Args:
            WD (float): The new working distance for the objective, in
            millimeters.
        """
        self._WD = WD

    def get_f_tube_lens_design(self):
        """
        Retrieves the designed focal length of the tube lens used with the
        objective in millimeters.

        Returns:
            float: The designed focal length of the tube lens.
        """
        return self._f_tube_lens_design

    def set_f_tube_lens_design(self, f_tube_lens_design):
        """
        Sets the designed focal length of the tube lens used with the
        objective.

        Args:
            f_tube_lens_design (float): The new designed focal length for the
            tube lens, in millimeters.
        """
        self._f_tube_lens_design = f_tube_lens_design

    def get_immersion(self):
        """
        Retrieves the type of immersion medium used with the objective.

        Returns:
            str: The type of immersion medium.
        """
        return self._immersion

    def set_immersion(self, immersion):
        """
        Sets the type of immersion medium used with the objective.

        Args:
            immersion (str): The new immersion medium for the objective.
        """
        self._immersion = immersion


if __name__ == '__main__':
    objective = BRamanObjective('N PLAN 10x/0.25')
    print(objective.get_metadata())
    objective = BRamanObjective('N PLAN 10x/0.25_2')
    print(objective.get_metadata())
