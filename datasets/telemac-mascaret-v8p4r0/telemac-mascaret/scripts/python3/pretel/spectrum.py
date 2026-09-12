#!/usr/bin/env python3
"""@author TELEMAC-MASCARET Consortium

   @brief Construct the spectrum on the boundary of a domain according to wave parameters
          from a result file.
"""
import argparse
from math import lgamma as gammaln, ceil
from os import remove, path

import numpy as np

from utils.exceptions import TelemacException
from config import add_config_argument, update_config
from data_manip.extraction.telemac_file import TelemacFile
from execution.telemac_cas import TelemacCas, get_dico

def create_frequencies_discretization(min_frequency, ratio, num_frequencies):
    """
    Create a set of frequencies as a geometric progression of ratio with minimal
    frequency min_frequency.
    @param min_frequency Minimal frequency.
    @param ratio Ratio of the geometric progression.
    @param num_frequencies Number of frequencies.
    """
    frequencies = np.array([min_frequency * ratio**i for i in range(num_frequencies)])
    return frequencies

def jonswap(frequencies, frequency_peak, gamma, alpha=0.0081):
    """
    Calculate the JONSWAP spectrum for a set of frequencies.
    @param frequencies The table of frequencies.
    @param frequency_peak The peak frequency.
    @param gamma A parameter of the JONSWAP function.
    @param alpha The Phillips constant.
    """
    gravity = 9.81
    deupi = 2*np.pi
    coefficient = alpha*gravity**2/(deupi**4)
    spectrum = np.zeros(len(frequencies))
    arg1 = np.zeros(len(frequencies))
    mask = frequencies < frequency_peak
    arg1[mask] = gamma**np.exp(-0.5*((frequencies[mask]-frequency_peak)/(0.07*frequency_peak))**2)
    mask = frequencies >= frequency_peak
    # arg1 arg2 and arg3 are temporary results.
    arg1[mask] = gamma**np.exp(-0.5*((frequencies[mask]-frequency_peak)/(0.09*frequency_peak))**2)
    arg2 = np.exp(-1.25*(frequency_peak/frequencies)**4)
    arg3 = coefficient/(frequencies**5)
    spectrum = arg1*arg2*arg3
    return spectrum

def spetma(frequencies, depth, spectrum):
    """
    @brief modify the spectrum to get a TMA spectrum according to jonswap formula
    @param frequencies, np array containing the frequencies
    @param depth water depth
    @param spectrum the jonswap spectrum
    """
    gravit = 9.81
    omegah = 2*np.pi*frequencies*np.sqrt(depth/gravit)
    mask = omegah < 1
    spectrum[mask] = spectrum[mask]*0.5*omegah[mask]**2
    mask = (omegah < 2) & (omegah > 1)
    spectrum[mask] = spectrum[mask]* (1.-0.5*(2.-omegah[mask])**2)
    return spectrum

def get_spectrum_data(cas):
    """
    @brief get the paramers necessary to make a spectrum
    @param cas the data that have been read in the steering file.
    """
    min_frequency = cas.get("MINIMAL FREQUENCY")
    ratio = cas.get("FREQUENTIAL RATIO")
    num_frequencies = cas.get("NUMBER OF FREQUENCIES")
    frequencies = create_frequencies_discretization(min_frequency, ratio, num_frequencies)
    num_directions = cas.get("NUMBER OF DIRECTIONS")
    teta = np.linspace(0, 2*np.pi, num_directions, endpoint=False)
    frabl = cas.get("BOUNDARY ANGULAR DISTRIBUTION FUNCTION")
    sprel = cas.get("BOUNDARY DIRECTIONAL SPREAD 1")
    peak_factor = cas.get("BOUNDARY PEAK FACTOR")
    return frequencies, teta, peak_factor, frabl, sprel

def fsprd1(teta, direction, sprel):
    """
    @brief compute the directionnal spreading
    as the choice 1 in TOMAWAC would do it.
    @param teta np array the discretised directions.
    @param direction main direction
    @param sprel spreading indice of the main direction.
    """
    fra = np.zeros(len(teta))
    ct1 = gammaln(sprel+0.5)
    ct2 = gammaln(sprel+1)
    normalise = 1./(np.pi**0.5*np.exp(ct1-ct2))
    arg = np.cos(teta-direction)
    mask = arg > 0
    fra[mask] = normalise*arg[mask]**(2*sprel)
    return fra

def calculate_spectrum(frequencies, teta, hm0, peak_frequency, direction, sprel, peak_factor):
    """
    @brief calculate the spectro angular energy as a JONSWAP function
           normalised to have hm0 as the wave height
    @param frequencies, np array containing the frequencies
    @param teta, np array containing the directions
    @param hm0 the wave height
    @param peak_frequency the peak frequency
    @param direction the main direction of waves
    @param sprel the spreading indice in the main direction
    @param peak_factor the peak factor of JONSWAP spectrum.
    """
    spectr = np.zeros(len(frequencies)*len(teta))
    gravit = 9.81
    alpha = 0.0624/(0.230+0.0336*peak_factor-0.185/(1.9+peak_factor)) \
               *(2*np.pi*peak_frequency)**4*hm0**2/gravit**2
    spectrum = jonswap(frequencies, peak_frequency, peak_factor, alpha=alpha)
    fra = fsprd1(teta, direction*2*np.pi/360., sprel)
    for freq in range(len(frequencies)):
        for dire in range(len(teta)):
            kkk = dire+len(teta)*freq
            spectr[kkk] = spectrum[freq]*fra[dire]
    return spectr

def create_mesh(frequencies, teta, med_file):
    """
    @brief create a Telemac file containing the spectro angular mesh.
    @param frequencies np array : the discretised frequencies
    @param teta np array : the discretised directions
    @param med_file string: the name of the file that will contain the mesh.
    """
    ndire = len(teta)
    nfreq = len(frequencies)
    npoints = nfreq*ndire
    nelem = (nfreq-1)*ndire

    points = np.zeros([npoints, 2])
    ickle = np.zeros([nelem, 4])
    for freq in range(nfreq):
        for dire in range(ndire):
            iii = dire+ndire*freq
            points[iii][0] = frequencies[freq]*np.sin(teta[dire])
            points[iii][1] = frequencies[freq]*np.cos(teta[dire])
    elem = 0
    for freq in range(nfreq-1):
        for dire in range(ndire):
            ickle[elem][0] = np.mod(elem+1, ndire)+freq*ndire
            elem = elem+1

    for elem in range(nelem):
        ickle[elem][1] = elem
        ickle[elem][2] = elem+ndire
        ickle[elem][3] = ickle[elem][0]+ndire
    if med_file == ' ':
        med_file = 'spectrum.spe'
        print('IMPOSED SPECTRA FILE was not specified in your steering file \n',\
               'The spectrum will be saved in file spectrum.spe')
    if path.exists(med_file):
        remove(med_file)
    res = TelemacFile(med_file, access='w')
    res.add_header('Ceci est un header', date=[2021, 2, 2, 0, 0, 0])
    res.add_mesh(points[:, 0], points[:, 1], ickle)
    return res

def spreading(sprel):
    """
    @brief calculate the spreading angle for the spreading coefficient
    @param sprel nparray containing the spreading coefficients.
    """
    theta = np.arange(91)
    thetarad = theta*np.pi/180.
    thetarad_2 = thetarad**2.
    cos_a = np.cos(thetarad)**(2.*sprel)
    coef = 1./(2.*np.trapz(cos_a*np.pi/180))
    anglespreading = np.sqrt(2*np.trapz(thetarad_2*cos_a*coef*np.pi/180))*180/np.pi
    return anglespreading

def get_spreading(angles_spread):
    """
    @brief find the correct spreading parameter for tomawac to get the spreading angle
    @param angles_spread nparray of spreading angles.
    """
    coefspread = np.zeros(len(angles_spread))
    sprel = np.arange(0.1, 100., 0.1)
    angspread_0 = np.zeros(len(sprel))

    for i, spread in enumerate(sprel):
        angspread_0[i] = spreading(spread)
    mask = angles_spread < min(angspread_0)
    coefspread[mask] = max(sprel)
    for i, angles in enumerate(angles_spread):
        ind = angspread_0 < angles
        if ind.any():
            coefspread[i] = sprel[ind][0]
        else:
            coefspread[i] = max(sprel)
    return coefspread

def get_boundary_points(mesh_file, bnd_file):
    """
    @brief return the coordinate of the points on ther boundary of a mesh
           The mesh is in the files named mesh_file
    @param mesh_file string contening the name of the mesh file
    @param bnd_file name of the file containing the boundary conditions
    """
    mesh = TelemacFile(mesh_file, bnd_file=bnd_file, access='r')
    mesh.read(mesh)
    nptfr = mesh.get_bnd_npoin()
    [_, lihbor, _, _, _] = mesh.get_bnd_info()
    list_x = []
    list_y = []
    for iptfr in range(nptfr):
        if lihbor[iptfr] == 5:
            xmesh = mesh.meshx[mesh._ikle_bnd[iptfr][0]]
            ymesh = mesh.meshy[mesh._ikle_bnd[iptfr][0]]
            list_x.append(xmesh)
            list_y.append(ymesh)
    datacoor = [np.array(list_x), np.array(list_y)]
    return datacoor


def initiate_spectrumfile(spectre, file_mesh, bnd_file, coortxt):
    """
    @brief add on a spectro angular telemacfile the variables that will contains the boundary
           the boundary points values and save the coordinates in a txt file
    @param spectre: the telemacfile that contains the spectro angular mesh
    @param mesh : the telemacfile that contains the domain
    @param coortxt : the name of the file that will contain the coordinates
    return datacoor list : the coordinates in x,y
           spectrum_var : the list of variables name.
    """
    mesh = TelemacFile(file_mesh, bnd_file=bnd_file, access='r')
    print('bnd_file',bnd_file)
    mesh.read(mesh)
    nptfr = mesh.get_bnd_npoin()
    [_, lihbor, _, _, _] = mesh.get_bnd_info()
    spectrum_var = []
    list_xy = []
    nptimpose = 0
    for iptfr in range(nptfr):
        if lihbor[iptfr] == 5:
            name = 'F{:05d}PT2D{:05d}'.format(iptfr+1, mesh._ikle_bnd[iptfr][0])
            spectrum_var.append(name)
            spectre.add_variable(name, 'UNITE SI        ')
            xmesh = mesh.meshx[mesh._ikle_bnd[iptfr][0]]
            ymesh = mesh.meshy[mesh._ikle_bnd[iptfr][0]]
            list_xy.append([xmesh, ymesh])
            nptimpose += 1
    header = str(nptimpose)+' '+str(0)+'\n'
    if coortxt == ' ':
        coortxt = 'coor.txt'
        print('FILE WITH COORDINATES OF SPECTRA TO IMPOSE was ',\
              'not specified in your steering file.\n',\
              'The coordinates will be saved in file coor.txt')
    savetxt(coortxt, list_xy, header=header)
    return [list_xy, spectrum_var]

def savetxt(txtfile, data, header=None):
    """
    @brief save on 4 column the set of coordinates of a list of point
           column 1 and 4 are useless but has to be present for TOMAWAC reading
    @param txtfile a string of the name of the file to save
    @param data the list of point to save
    @param header a possible header if needed.
    """
    if path.exists(txtfile):
        remove(txtfile)
    with open(txtfile, 'w', encoding='utf-8') as filetxt:
        filetxt.write(header)
        for i in range(len(data)):
            filetxt.write(str(i)+' '+str(data[i][0])+' '+str(data[i][1])+' '+str(0.)+'\n')

def addvarlist(telmacfile, nomvar, var, timestep):
    """
    @brief add values to a telemacfile of a list of variable at a timestep
    """
    for i, nom in enumerate(nomvar):
        telmacfile.add_data_value(nom, timestep, var[i])

def get_data_res(res_file, listvar, coor):
    """
    @brief get all the value of the res_file for variables contains in listvar
           at the points given in the array coor
    @param res_file a string containing the name of the result file
    @param listvar a list of string containing the desired variables
    @param coor an array containing all the coordinates of the desired nodes.
    """
    if not path.exists(res_file):
        raise NameError('{} does not exist'.format(res_file))
    res = TelemacFile(res_file, access='r')
    res.read(res)
    var_res = []
    for var in listvar:
        if var in res.varnames:
            data = res.get_timeseries_on_points(var, coor)
            var_res.append(data)
        elif var == "PEAK FREQ FPR5" and "PEAK PERIOD TPR5" in res.varnames:
            data = res.get_timeseries_on_points("PEAK PERIOD TPR5", coor)
            var_res.append(1./data)
        else:
            raise TelemacException("{} is not in {}".format(var, res.varnames))
    return  res.times, var_res

def calculate_spectrum_in_time(spectre, spectrum_var, var, itermax, time_res,\
                              frequencies, teta, peak_factor):
    """
    @brief calculate spectrums based on sea state variables
           and save the spectrums in a boundary spectrum file
    @param spectre Telemacfile that will contain the spectrums
    @param spectrum_var list of strings containing the name of points
           where we save the spectrum
    @param var np array containing the sea state variables for each point
           and each time step
    @param itermax integer, the number of time step we need to calculate the spectrum
    @param time_res the list of time we have the results of the variables
    @param frequencies nparray the discretised frequencies
    @param teta np array the discretised directions
    @param peak_factor the JONSWAP peak factor
    """
    for itime in range(itermax+1):
        if itime != 0:
            spectre.add_time_step(time_res[itime])
        spectrum = []
        sprel = get_spreading(var[3, :, itime])
        for i in range(len(var[0])):
            spectrum.append(calculate_spectrum(frequencies, teta, var[0, i, itime],\
                            var[2, i, itime], var[1, i, itime], sprel[i], peak_factor))
        addvarlist(spectre, spectrum_var, spectrum, itime)
    spectre.write()
    spectre.close()


def main():
    """
    Construct a spectrum on the boundary of a domain and save it in a file that
    a steering file needs. The spectrum is made with sea state variables that
    comes from a previous calculation.
    """
    parser = argparse.ArgumentParser(description='Construct a Spectrum')

    parser.add_argument("cas_file",
                        default=None,
                        help="The TOMAWAC cas file")

    parser.add_argument("--res",
                        dest='res_file',
                        default=None,
                        required=True,
                        help="The file that contains the HM0, frequency peak, direction...")

    parser = add_config_argument(parser)
    args = parser.parse_args()
    update_config(args)
    cas_file = args.cas_file
    res_file = args.res_file

    cas = TelemacCas(cas_file, get_dico('tomawac'), check_files=False)

    [frequencies, teta, peak_factor, _, _] = get_spectrum_data(cas)
    spectre_file = cas.get("IMPOSED SPECTRA FILE")
    spectre = create_mesh(frequencies, teta, spectre_file)
    coortxt = cas.get('FILE WITH COORDINATES OF SPECTRA TO IMPOSE')
    file_mesh = cas.get("GEOMETRY FILE")
    bnd_file = cas.get("BOUNDARY CONDITIONS FILE")
    [bccoor, spectrum_var] = initiate_spectrumfile(spectre, file_mesh, bnd_file, coortxt)

    var_sea = ['WAVE HEIGHT HM0', 'MEAN DIRECTION', 'PEAK FREQ FPR5', 'WAVE SPREAD']
    time_res, var = get_data_res(res_file, var_sea, bccoor)
    states = np.array(var)
    delta_t = cas.get("TIME STEP")
    ntimestep = cas.get("NUMBER OF TIME STEP")
    itermax = ceil(ntimestep*delta_t/(time_res[1]-time_res[0]))
    calculate_spectrum_in_time(spectre, spectrum_var, states, itermax, time_res,\
                              frequencies, teta, peak_factor)
    print('The spectrum has been saved in', spectre_file)

if __name__ == "__main__":
    main()
