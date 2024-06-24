"""
Implementation of a simulated galvanometer module.

Copyright (C) 2024 Rowan Nicholls <rowan.nicholls@dtc.ox.ac.uk>

This file is part of Microscope.

Microscope is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Microscope is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Microscope.  If not, see <http://www.gnu.org/licenses/>.
"""
# Standard library
import logging
# Custom module
from microscope.abc import Device

# Set up configuration for the logger
logging.basicConfig(
    filename='galvo.log',
    level=logging.INFO,
    filemode='w',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
_logger = logging.getLogger(__name__)


class Galvo(Device):
    """
    Galvanometer devices.

    Galvos detect and measure electrical current via the deflection of a
    needle. They are used to precisely control the position and orientation of
    mirrors and other components, allowing for fine adjustments in the light
    path. This is necessary for high-resolution imaging and accurate scanning
    techniques such as laser scanning microscopy.
    """

    def __init__(self, **kwargs):
        """Initialise."""
        _logger.info('A galvanometer device is initialised.')

    def set_current(self, current: int) -> None:
        """Set the electrical current value."""
        _logger.info('The current is set.')
        self.current = current

    def get_current(self) -> int:
        """Get the electrical current reading."""
        _logger.info('The current is got.')
        return self.current

    def _do_shutdown(self) -> None:
        _logger.info('A galvanometer device is shut down.')
        pass


class SimulatedGalvo(Galvo):
    """Simulated galvanometer devices."""

    def __init__(self, **kwargs):
        """Initialise."""
        _logger.info('A simulated galvanometer device is initialised.')

        # Set a value for the electrical current
        self.set_current(10)

    def _do_shutdown(self) -> None:
        _logger.info('A simulated galvanometer device is shut down.')
        pass


if __name__ == '__main__':
    print('Hello, World!')

    # Instantiate a real galvo
    actual_galvo = Galvo()
    # Shutdown the real galvo
    actual_galvo.shutdown()

    # Instantiate a simulated galvo
    simulated_galvo = SimulatedGalvo()
    print(simulated_galvo.get_current())
    simulated_galvo.shutdown()
    print(simulated_galvo.get_current())
