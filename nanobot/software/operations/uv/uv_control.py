"""
.. module:: uv_control
    :platform: Unix
    :synopsis: Module for interfacing with UV/Vis Spectrometer in the Base Layer

.. moduleauthor:: Graham Keenan <https://github.com/ShinRa26>

"""

import os
import sys
import inspect
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
root_path = os.path.join(HERE, "..", "..")
op_path = os.path.join(HERE, "..")
sys.path.append(op_path)
sys.path.append(root_path)

import constants.common as cst
from utils import json_utils as json
from base_layer.spectrometer.oceanoptics import Spectrometer


class UVControl(Spectrometer):
    """
    Operational class for interfacing with the UV spectrometer in the base layer.
    Allows obtaining spectra and saving them to image and json format

    Inherits:
        Spectrometer: Base Spectrometer layer
    """
    def __init__(self, integration_time=1):
        Spectrometer.__init__(
            self,
            cst.UV_SPECTROMETER,
            integration_time=integration_time
        )


    def obtain_reference_spectrum(self, img_path, json_path):
        """
        Obtains a reference spectrum.
        This outputs the data as wavelengths/intensity as necessary for Beer-Lambert transformations

        Args:
            img_path (str): Path to save the image file
            json_path (str): Path to save the json file

        """
        spectrum_data = self.get_spectrum()

        # Trims the data to be within a certain wavelength range
        wavelengths = np.array(spectrum_data[cst.WAVELENGTH])
        intensities = np.array(spectrum_data[cst.INTENSITY])

        # Clear any previous data
        plt.clf()
        plt.cla()

        plt.plot(wavelengths, intensities, color="black", linewidth=0.5)
        plt.title("Referece UV/Vis Spectrum")
        plt.xlabel("Wavelength")
        plt.ylabel("Intensity")
        plt.savefig(img_path)

        json.write(spectrum_data, json_path)


    def obtain_spectrum_image_only(self, ref_path, img_path):
        """
        Obtains a spectrum and outputs to image format only

        Args:
            ref_path (str): Path to the reference spectrum json file
            img_path (str): Path to save the image file

        Returns:
            output_data (Dict): Dictionary containing the spectrum data
        """
        output_data = {}
        spectrum_data = self.get_spectrum()
        ref_data = json.read(ref_path)

        ref_intensities = ref_data[cst.INTENSITY]
        spectrum_intensities = spectrum_data[cst.INTENSITY]

        wavelengths = np.array(spectrum_data[cst.WAVELENGTH])
        output_data[cst.WAVELENGTH] = wavelengths.tolist()

        absorbances = []
        for ref, measured in zip(ref_intensities, spectrum_intensities):
            try:
                if ref == 0 or measured == 0:
                    continue
                absorbances.append(np.log10(ref/measured))
            except:
                break

        output_data[cst.ABSORBANCE] = absorbances
        output_data[cst.INTENSITY] = spectrum_intensities

        # Clears any previous plots from graph
        plt.clf()
        plt.cla()

        absorbances = np.array(absorbances)

        plt.plot(wavelengths, absorbances, color="black", linewidth=0.5)
        plt.title("UV/Vis Spectrum")
        plt.xlabel("Wavelength")
        plt.ylabel("Absorbance")

        # Add an annotated line for maximum absorbance
        plt.gca().set_ylim(bottom=0)
        vert = wavelengths[np.argmax(absorbances)]
        max_y = max(absorbances)
        leg_label = f"Maximum: {vert:.2f}nm"
        plt.vlines(x=vert, ymin=0, ymax=max_y, color="g", zorder=3, label=leg_label)
        leg = plt.legend()

        # Set linewidth of legend to 5.0
        for legobj in leg.legendHandles:
            legobj.set_linewidth(5.0)

        plt.savefig(img_path)

        return output_data


    def obtain_spectrum(self, ref_input_path, json_path, img_path):
        """
        Obtains a spectrum and outputs to json and image format

        Args:
            ref_input_path (str): Path to the reference spectrum json data
            json_path (str): Path to save the json file
            img_path (str): Path to save the image file

        """
        data = self.obtain_spectrum_image_only(
            ref_input_path,
            img_path
        )
        json.write(data, json_path)
