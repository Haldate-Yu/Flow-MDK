# -*- coding: utf-8 -*-
"""
    Python wrapper to the Fortran APIs of Telemac 2D

    Author(s): Fabrice Zaoui, Yoann Audouin, Cedric Goeury, Renaud Barate

    Copyright EDF 2016
"""

import os

import numpy as np
from telapy.api.api_module import ApiModule
from utils.exceptions import TelemacException
from utils.polygon import is_in_polygon


class Telemac2d(ApiModule):
    """The Telemac 2D Python class for APIs"""
    _instanciated = False

    def __new__(cls, *args, **kwargs):
        if cls._instanciated:
            raise TelemacException("a Telemac2d instance already exists")
        instance = ApiModule.__new__(cls)
        cls._instanciated = True
        return instance

    def __init__(self, casfile,
                 user_fortran=None,
                 dicofile=None,
                 lang=2, stdout=6,
                 comm=None,
                 log_lvl='INFO',
                 recompile=True):
        """
        Constructor for Telemac2d

        @param casfile (string) Name of the steering file
        @param user_fortran (string) Name of the user Fortran
        @param dicofile (string) Path to the dictionary
        @param lang (int) Language for ouput (1: French, 2:English)
        @param stdout (int) Where to put the listing
        @param comm (MPI.Comm) MPI communicator
        @param recompile (boolean) If true recompiling the API
        @param log_lvl (string) Logger level
        """
        if dicofile is None:
            hometel = os.getenv("HOMETEL")
            if hometel is not None:
                default_dicofile = os.path.join(os.getenv("HOMETEL"),
                                                "sources",
                                                "telemac2d",
                                                "telemac2d.dico")
            else:
                default_dicofile = 'telemac2d.dico'

            dicofile = default_dicofile
        super(Telemac2d, self).__init__("t2d", casfile, user_fortran,
                                        dicofile, lang, stdout,
                                        comm, recompile, log_lvl=log_lvl)

        self._saved = {}

    def _save_variable(self, variable, block_len=1):
        """
        Save a variable in an instance dictionary.
        
        @param variable (string) The variable name.
        @param block_len (int) The number of elements of a block variable.
        """
        self._saved[variable] = []
        for i in range(block_len):
            value = self.get_array(f'MODEL.{variable}', i)
            self._saved[variable].append(value)

    def save_state(self):
        """
        Save the hydraulic state and variables required for a complete restart.
        """
        # Prepare the description of the saved state
        iturb = self.get('MODEL.ITURB')
        ntrac = self.get('MODEL.NTRAC')
        iordrh = self.get('MODEL.IORDRH')
        iordru = self.get('MODEL.IORDRU')
        seccurrents = self.get('MODEL.SECCURRENTS')
        nestor = self.get('MODEL.NESTOR')

        self._saved = {}

        # Basic hydraulic state
        self._save_variable('WATERDEPTH')
        self._save_variable('VELOCITYU')
        self._save_variable('VELOCITYV')
        # Mutable parameters for controlled friction
        self._save_variable('CHESTR')
        # Turbulence scheme
        if iturb == 3:
            self._save_variable('AK')
            self._save_variable('EP')
        if iturb == 6:
            self._save_variable('VISCSA')
        # Increments
        if iordrh in (1,2):
            self._save_variable('INCWATERDEPTH')
            if iordrh == 2:
                self._save_variable('INCWATERDEPTHN')
        if iordru == 2:
            self._save_variable('INCVELOCITYU')
            self._save_variable('INCVELOCITYV')
        # Secondary currents
        if seccurrents:
            self._save_variable('SEC_R')
        # Reference level for NESTOR
        if nestor:
            self._save_variable('ZREFLEVEL')
        # Tracers
        if ntrac > 0:
            self._save_variable('TRACER', ntrac)

    def restore_state(self):
        """
        Restore the hydraulic state.
        """
        for variable, array in self._saved.items():
            for index, value in enumerate(array):
                self.set_array(f'MODEL.{variable}', value, index)

    def get_state(self):
        """
        Get the hydraulic state

        @returns the hydraulic state: depth (m) .. u_vel (m/s) .. v_vel (m/s)
        """
        depth = self.get_array('MODEL.WATERDEPTH')
        u_vel = self.get_array('MODEL.VELOCITYU')
        v_vel = self.get_array('MODEL.VELOCITYV')
        return depth, u_vel, v_vel

    def set_state(self, hval, uval, vval):
        """
        Set the hydraulic state: hval (m) .. uval (m/s) .. vval (m/s)

        @param hval Water depth value
        @param uval Velocity U value
        @param vval Velocity V value
        """
        self.set_array('MODEL.WATERDEPTH', hval)
        self.set_array('MODEL.VELOCITYU', uval)
        self.set_array('MODEL.VELOCITYV', vval)

    def show_state(self, show=True):
        """
        Show the hydraulic state with matplotlib

        @param show Display the graph (Default True)

        @returns the figure object
        """
        import matplotlib.pyplot as plt
        if self.coordx is not None:
            _, _, _ = self.get_mesh()
        values = self.get_state()
        fig = plt.figure()
        plt.subplot(1, 2, 1)  # water levels
        plt.tripcolor(self.coordx, self.coordy, self.tri, values[0],
                      shading='gouraud', cmap=plt.cm.winter)
        plt.colorbar()
        plt.title('Water levels (m)')
        plt.xlabel('X-coordinate (m)')
        plt.ylabel('Y-coordinate (m)')
        plt.subplot(1, 2, 2)  # velocity
        uvnorm = np.sqrt(values[1]**2 + values[2]**2)
        plt.quiver(self.coordx, self.coordy, values[1], values[2], uvnorm,
                   units='xy', angles='uv', scale=0.01)
        plt.colorbar()
        plt.title('Velocity field (m/s)')
        plt.xlabel('X-coordinate (m)')
        plt.ylabel('Y-coordinate (m)')
        if show:
            plt.show()
        return fig

    def set_bathy(self, bathy, polygon=None):
        """
        Set a new bathy in the geometry file

        @param bathy Array containing the new bathymetry for each point
        @param polygon Polygon on which to modify the bathymetry
        """
        if polygon is None:
            self.set_array("MODEL.BOTTOMELEVATION", bathy)
        else:
            coordx = self.get_array("MODEL.X")
            coordy = self.get_array("MODEL.Y")
            for i, value in enumerate(bathy):
                if is_in_polygon(coordx[i], coordy[i], polygon):
                    self.set("MODEL.BOTTOMELEVATION",
                             value, i=i)

        return

    def __del__(self):
        """
        Destructor
        """
        Telemac2d._instanciated = False
