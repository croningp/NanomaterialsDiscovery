"""
.. module:: Spectrometer
    :platform: Unix
    :synopsis: Module for interfacing with OceanOptics Spectrometers

.. moduleauthor:: Graham Keenan <https://github.com/ShinRa26>

"""

import time
import numpy as np
import seabreeze.spectrometers as sb


""" Constants """
SCAN_AVERAGE = 5 # Number of scans performed
UV_TRIM_MIN = 400 # Minimum wavelength cutoff (For trimming)
UV_TRIM_MAX = 950 # Maximum wavelength cutoff (For trimming)
WAVELENGTH = "wavelength"
INTENSITY = "intensities"


# Spectrometer Types:
SPECS = {
    "UV": "2192"
}

class UnsupportedSpectrometer(Exception):
    """Exception for unsupported spectrometer types
    """


class NoSpectrometerDetected(Exception):
    """Exception for when no spectrometer is detected
    """


def _get_spectrometer(spec_type: str) -> str:
    """Gets the Spectrometer from Seabreeze that matches given type

    Arguments:
        spec_type {str} -- Type of spectrometer to look for

    Raises:
        UnsupportedSpectrometer -- If the spec_type is not present

    Returns:
        str -- Name of the spectrometer
    """

    devices = sb.list_devices()

    if not devices:
        raise NoSpectrometerDetected("Are the spectrometers plugged in?")
    if spec_type in SPECS.keys():
        for dev in devices:
            if SPECS[spec_type] in str(dev):
                return dev
    raise UnsupportedSpectrometer("Spectrometer {} unsupported!".format(spec_type))


class Spectrometer(object):
    """
    Base class for interfacing with the OceanOptics spectrometers
    Seabreeze Documentation: (https://github.com/ap--/python-seabreeze)
    """
    def __init__(self, spec_type: str, integration_time=1):
        self.spec_type = spec_type
        self.spectra_time_delay = 0.01
        self.spec = _get_spectrometer(spec_type)
        self.integration_time = integration_time * 10e3


    def get_spectrum(self, spectra_time=20) -> dict:
        """
        Reads from the spectrometer to return the spectrum data

        Keyword Arguments:
            spectra_time (int): Number of seconds to obtain the spectrum for

        Returns:
            data (Dict): Dictionary containing the spectrum's wavelength and intensity data
        """

        spectrum = {}

        curr_time = time.time()

        try:
            # Open spectrometer connection
            spectrometer = sb.Spectrometer(self.spec)
            spectrometer.integration_time_micros(self.integration_time)

            # Obain spectra for X time
            while time.time() < curr_time + spectra_time:
                wavelengths, intensities = spectrometer.spectrum()
                time.sleep(self.spectra_time_delay)

            trimmed = self.trim_data(wavelengths)

            # Trim intensities for UV
            if self.spec_type == 'UV':
                intensities = intensities[trimmed]
                wavelengths = wavelengths[trimmed]

            spectrum[WAVELENGTH] = wavelengths.tolist()
            spectrum[INTENSITY] = intensities.tolist()

            # Close spectrometer connection
            spectrometer.close()
        except Exception as e:
            print(f"Error accessing device: {e}")
            spectrometer.close()

        return spectrum


    def set_time_delay(self, seconds: int):
        """ Sets the time time delay for accessing the Spectrometer

        Arguments:
            seconds {int} -- Time delay
        """
        self.time_delay = seconds


    def set_integration_time(self, integration_time: int):
        """Sets the integration time for the spectrometer

        Arguments:
            integration_time {int} -- Integration time in seconds
        """

        self.integration_time = integration_time * 10e3


    def trim_data(
            self,
            data,
            above_index=UV_TRIM_MIN,
            below_index=UV_TRIM_MAX
        ) -> np.ndarray:
        """
        Trims the spectrum data to be within a specific wavelength range

        Args:
            data (List): List of wavelengths to trim

        Keyword Arguments:
            above_index (int): Minimum position on the X axis to start from
            below_index (int): Maximum position on the X axis to end from

        Returns:
            trimmed (NpArray): Wavelengths between TRIM_MIN and TRIM_MAX range
        """
        above_ind = np.array(data) > above_index
        below_ind = np.array(data) < below_index

        return np.logical_and(above_ind, below_ind)
