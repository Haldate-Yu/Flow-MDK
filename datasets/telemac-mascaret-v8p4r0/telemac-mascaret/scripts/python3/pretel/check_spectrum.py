#!/usr/bin/env python3
"""@author TELEMAC-MASCARET Consortium

   @brief Check if discretization parameters are able to represent the chosen spectrum.
          It uses a JONSWAP spectrum with a chosen peak frequency.
          This spectrum is typically the imposed spectrum at the boundary of TOMAWAC.
"""
import argparse

import numpy as np

from config import add_config_argument, update_config
from execution.telemac_cas import TelemacCas, get_dico
from pretel.spectrum import jonswap, get_spectrum_data

def plot(frequencies, spectrum, file_output=None):
    """
    Plot the spectrum and export the output to a PNG file.
    @param frequencies Abscissae.
    @param spectrum The spectrum to plot.
    @param file_output The name of the exported PNG file.
    """
    import matplotlib.pyplot as plt
    _, axe = plt.subplots(figsize=(12, 10))
    axe.plot(frequencies, spectrum)
    axe.set_xlabel("frequencies")
    axe.set_ylabel("spectrum")
    if file_output is not None:
        plt.savefig(file_output)
        plt.close(1)
        print('Exporting the output to ', file_output)
    else:
        plt.show()
    del plt

def main():
    """
    Plot the spectrum defined in a TOMAWAC cas file.
    """
    parser = argparse.ArgumentParser(description='Check spectral discretization')

# ~~~~ Environment ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    parser.add_argument("cas_file",
                        default=None,
                        help="The TOMAWAC cas file")

    parser.add_argument("--png",
                        dest='png_file',
                        default=None,
                        help="Export the plot output to a PNG file.")

    parser = add_config_argument(parser)
    args = parser.parse_args()
    update_config(args)
    png_file = args.png_file
    cas_file = args.cas_file
    cas = TelemacCas(cas_file, get_dico('tomawac'), check_files=False)
    [frequencies, _, peak_factor, _, _] = get_spectrum_data(cas)

    peak_frequency = cas.get("BOUNDARY PEAK FREQUENCY")
    alpha = cas.get("BOUNDARY PHILLIPS CONSTANT")
    hm0 = cas.get("BOUNDARY SIGNIFICANT WAVE HEIGHT")
    gravit = 9.81
    deupi = 2*np.pi
    alpha = 0.0624/(0.230+0.0336*peak_factor-0.185/(1.9+peak_factor)) \
              *(deupi*peak_frequency)**4*hm0**2/gravit**2
    spectrum = jonswap(frequencies, peak_frequency, peak_factor, alpha=alpha)
    plot(frequencies, spectrum, file_output=png_file)

if __name__ == "__main__":
    main()
