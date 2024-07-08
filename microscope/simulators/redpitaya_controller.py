"""
Implementation of a simulated Red Pitaya module.

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
import typing
# Custom module
import microscope.abc

# Set up configuration for the logger
logging.basicConfig(
    filename='redpitaya_controller.log',
    level=logging.INFO,
    filemode='w',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
_logger = logging.getLogger(__name__)


class RedPitaya(microscope.abc.Controller):
    """Red Pitaya devices."""

    def __init__(self, **kwargs):
        """Initialise."""
        _logger.info('A Red Pitaya device is initialised.')
        self._devices: typing.Mapping[str, microscope.abc.Device] = {}

    @property
    def devices(self) -> typing.Mapping[str, microscope.abc.Device]:
        return self._devices


class SimulatedRedPitaya(RedPitaya):
    """Simulated Red Pitaya devices."""

    def __init__(self, **kwargs):
        """Initialise."""
        _logger.info('A simulated Red Pitaya device is initialised.')
        self._devices: typing.Mapping[str, microscope.abc.Device] = {}


if __name__ == '__main__':
    print('Hello, World!')

    # Instantiate a real Red Pitaya
    actual_redpitaya = RedPitaya()
    # Shutdown the real Red Pitaya
    actual_redpitaya.shutdown()

    # Instantiate a simulated Red Pitaya
    simulated_redpitaya = SimulatedRedPitaya()
    simulated_redpitaya.shutdown()
