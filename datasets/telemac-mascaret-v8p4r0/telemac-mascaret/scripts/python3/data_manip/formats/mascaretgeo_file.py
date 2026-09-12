from collections import OrderedDict
import os.path

from data_manip.formats.mascaret_file import Reach, Section
from utils.exceptions import MascaretException



class MascaretGeoFile():
    """
    Parse Mascaret geometry file (geo/geoC/georef/georefC)
    Handles multiple reaches
    TODO: handle major/minor bed

    Attributs:
    - file_name (str) file name
    - fformat (str) file format ('opt' or 'rub')

    - has_ref (bool): has X and Y coordinates for points
        (and hydraulic axis position)
    - has_layers (bool): has sediment layers
    - nlayers (int): number of layers
    - layer_names (list): list of layer names
    """
    OUTPUT_FLOAT_FMT = '%.6f'

    def __init__(self, file_name, load_file=True, fformat=None, mode='read'):
        """
        @param file_name (str) file name
        @param load_file (bool) option to activate loading of the file
        @param fformat (str) file format ('opt' or 'rub')
        @param mode (str) define the mode for the class,
            'read' by default to read a file,
            anything else to create a file
        """
        self.file_name = file_name
        self.reaches = OrderedDict()

        # Layers for sediments (Courlis)
        self.nlayers = 0
        self.layer_names = []

        if mode == 'read':
            # File format information
            if fformat is None:
                self.fformat = os.path.splitext(file_name)[1][1:]
            else:
                self.fformat = fformat.lower().strip()
            if self.fformat not in ('geo', 'geoC', 'georef', 'georefC'):
                raise NotImplementedError(
                    'Format `%s` not supported,\
                     only geo, geoC, georef and georefC formats are supported\
                     as input' % self.fformat)
            self.has_ref = 'ref' in self.fformat

            # Layers for sediments (Courlis)
            self.has_layers = self.fformat.endswith('C')

            if load_file:
                # Load file content
                self.load()

    def load(self):
        """
        Load Mascaret geometry file (geo/georef)
        """
        with open(self.file_name, 'r') as filein:
            reach = None
            reach_id_curr = 1
            section_id = 0
            section_name = ''
            section_pk = -1.0
            dist, x_list, y_list, z_list, topo_bath_list, layers_elev_list = \
                [], [], [], [], [], []
            x_axis, y_axis = None, None

            for line in filein:
                if line.startswith('#'):
                    # Ignore comment line
                    pass
                elif line.upper().startswith('PROFIL'):
                    if dist:
                        # Add previous Section
                        section = Section(section_id, section_pk, section_name)
                        if x_axis is not None and y_axis is not None:
                            section.set_axis(x_axis, y_axis)
                        if self.has_ref:
                            section.set_points_from_xyz(x_list, y_list, z_list,
                                                        topo_bath_list)
                        else:
                            section.set_points_from_trans(dist, z_list,
                                                          topo_bath_list)
                        section.distances = dist
                        if self.has_layers:
                            section.add_layers_from_elevations(
                                    layers_elev_list)
                        reach.add_section(section)

                    if self.has_ref:
                        _, reach_name, section_name, pk_str, x1, y1, x2, y2,\
                         _, x_axis, y_axis = line.split()
                        x_axis = float(x_axis)
                        y_axis = float(y_axis)
                    else:
                        _, reach_name, section_name, pk_str = line.split()

                    # Create first reach for initialisation
                    if reach is None:
                        reach = Reach(reach_id_curr, reach_name)
                        self.add_reach(reach)
                        reach_id_curr += 1

                    # Create a new reach if necessary
                    if reach_name != reach.name:
                        reach = Reach(reach_id_curr, reach_name)
                        self.add_reach(reach)
                        reach_id_curr += 1

                    # Reset variables to store section
                    section_pk = float(pk_str)
                    dist, x_list, y_list, z_list, topo_bath_list, \
                        layers_elev_list = [], [], [], [], [], []
                    section_id += 1
                else:
                    list_line = line.split()

                    if self.has_ref and self.has_layers is False:
                        dist_str = list_line[0]
                        z_str = list_line[1]
                        if "T" in list_line or "B" in list_line:
                            shift = 0
                            topo_bath = list_line[2]
                        else:
                            shift = -1
                            topo_bath = "B"

                        x_list.append(float(list_line[shift + 3]))
                        y_list.append(float(list_line[shift + 4]))

                    elif self.has_ref and self.has_layers:
                        dist_str = list_line[0]
                        z_str = list_line[1]
                        if "T" in list_line or "B" in list_line:
                            shift = 0
                            topo_bath = list_line[-3]
                        else:
                            shift = 1
                            topo_bath = "B"

                        layers_elev = list_line[2:shift - 3]

                        x_list.append(float(list_line[-2]))
                        y_list.append(float(list_line[-1]))

                        layers_elev = [float(elev) for elev in layers_elev]

                        if self.nlayers == 0:
                            self.nlayers = len(layers_elev)

                    elif self.has_ref is False and self.has_layers:
                        dist_str = list_line[0]
                        z_str = list_line[1]
                        if "T" in list_line or "B" in list_line:
                            layers_elev = list_line[2:-1]
                            topo_bath = list_line[-1]
                        else:
                            layers_elev = list_line[2:]
                            topo_bath = "B"

                        layers_elev = [float(elev) for elev in layers_elev]

                        if self.nlayers == 0:
                            self.nlayers = len(layers_elev)

                    else:
                        dist_str = list_line[0]
                        z_str = list_line[1]

                        if "T" in list_line or "B" in list_line:
                            topo_bath = list_line[2]
                        else:
                            topo_bath = "B"

                    # Add new point to current section
                    dist.append(float(dist_str))
                    z_list.append(float(z_str))
                    topo_bath_list.append(topo_bath)
                    if self.has_layers:
                        layers_elev_list.append(layers_elev)

            # Add last section
            section = Section(section_id, section_pk, section_name)
            if x_axis is not None and y_axis is not None:
                section.set_axis(x_axis, y_axis)
            if self.has_ref:
                section.set_points_from_xyz(x_list, y_list, z_list,
                                            topo_bath_list)
            else:
                section.set_points_from_trans(dist, z_list, topo_bath_list)
            section.distances = dist
            if self.has_layers:
                section.add_layers_from_elevations(layers_elev_list)
                self.layer_names = section.layer_names
            reach.add_section(section)

    def save(self, output_file_name):
        """
        Save Mascaret geometry file (geo/georef)
        @param output_file_name (str) output file name
        """
        fformat = os.path.splitext(output_file_name)[1]
        if fformat == '.geo':
            ref, layers = False, False
        elif fformat == '.georef':
            ref, layers = True, False
        elif fformat == '.geoC':
            ref, layers = False, True
        else:  # georefC
            ref, layers = True, True

        if ref and not self.has_ref:
            raise MascaretException('Could not write `%s` format without\
                    any geo-referenced data' % fformat)

        with open(output_file_name, 'w', encoding="utf-8") as fileout:
            for _, reach in self.reaches.items():

                for sec in reach:
                    positions_str = ''
                    if ref:
                        # Get river_banks and `AXE` coordinates if necessary
                        x_axis, y_axis = sec.axis
                        positions_str += '%f %f %f %f' %\
                            (sec.x[0], sec.y[0], sec.x[-1], sec.y[-1])
                        positions_str += ' AXE %f %f' % (x_axis, y_axis)

                    # Write profile header
                    fileout.write(
                        'Profil %s %s %f %s\n' %
                        (reach.name, sec.name, sec.pk, positions_str))

                    # Write points and layers if necessary
                    if not ref and not layers:
                        for dist, z, topo_bath in zip(sec.distances, sec.z,
                                                      sec.topo_bath):
                            fileout.write('%f %f %s\n' % (dist, z, topo_bath))

                    elif ref and not layers:
                        for dist, x, y, z, topo_bath in zip(sec.distances,
                                                            sec.x,
                                                            sec.y,
                                                            sec.z,
                                                            sec.topo_bath):
                            fileout.write('%f %f %s %f %f\n'
                                          % (dist, z, topo_bath, x, y))

                    elif not ref and layers:
                        for i, (dist, z, topo_bath) in \
                                enumerate(zip(sec.distances, sec.z,
                                              sec.topo_bath)):
                            if self.nlayers == 0:
                                layers_str = ''
                            else:
                                layers_str = ' ' +\
                                        ' '.join(
                                                [MascaretGeoFile.OUTPUT_FLOAT_FMT % zl
                                                    for zl in sec.layers_elev[:, i]])

                            try:
                                fileout.write('%f %f %s %s\n' %
                                            (dist, z, layers_str, topo_bath))
                            except Exception as e:
                                raise e

                    elif ref and layers:
                        for i, (dist, x, y, z, topo_bath) in enumerate(zip(sec.distances,
                            sec.x,
                            sec.y,
                            sec.z,
                            sec.topo_bath)):

                            if self.nlayers == 0:
                                layers_str = ''
                            else:
                                layers_str = ' ' + ' '\
                                        .join([MascaretGeoFile.OUTPUT_FLOAT_FMT %
                                            zl for zl in sec.layers_elev[:, i]])

                            try:
                                fileout.write('%f %f %s %s %f %f\n'
                                          % (dist, z, layers_str,
                                             topo_bath, x, y))
                            except Exception as e:
                                raise e


    def __repr__(self):
        return 'MascaretGeoFile: %s' % self.file_name

    def save_precourlis(self, output_file_name, crs="EPSG:2154"):
        """
        Method to export a MascaretGeoFile into the PreCourlis format
        (geopackage with specific attributes)
        It requires X and Y GIS coordinates (georef)
        """
        import fiona

        properties = [('sec_id', 'int'),
                      ('sec_name', 'str:80'),
                      ('abs_long', 'float'),
                      ('axis_x', 'float'),
                      ('axis_y', 'float'),
                      ('layers', 'str:254'),
                      ('p_id', 'str:100000'),
                      ('topo_bat', 'str:100000'),
                      ('abs_lat', 'str:100000'),
                      ('zfond', 'str:100000')]

        for layer_name in self.layer_names:
            properties.append((layer_name, 'str'))

        schema = {'geometry': 'LineString',
                  'properties': OrderedDict(properties)}

        dict_lines = []

        reach = self.reaches[1]
        for sec in reach:
            coord = []
            for x, y in zip(sec.x, sec.y):
                coord.append((x, y))

            properties_sec = [('sec_id', sec.id),
                              ('sec_name', sec.name),
                              ('abs_long', sec.pk),
                              ('axis_x', sec.axis[0]),
                              ('axis_y', sec.axis[1]),
                              ('layers', ','.join(sec.layer_names)),
                              ('p_id', ','.join(map(str,
                                                range(sec.nb_points)))),
                              ('topo_bat', ','.join(sec.topo_bath)),
                              ('abs_lat', ','.join(map(str, sec.distances))),
                              ('zfond', ','.join(map(str, sec.z)))]

            for i, layer_name in enumerate(self.layer_names):
                properties_sec.append((layer_name, ",".join(map(
                    str, sec.layers_elev[i, :]))))

            dict_lines.append({'geometry': {'type': 'LineString',
                               'coordinates': coord},
                               'properties': OrderedDict(properties_sec)})

        with fiona.open(output_file_name, 'w', driver='GPKG', crs=crs,
                        schema=schema) as shp:
            for dict_line in dict_lines:
                shp.write(dict_line)

    def add_reach(self, reach):
        """
        Add a single reach
        @param reach (Reach) reach to add
        """
        self.reaches[reach.id] = reach

    def add_constant_layer(self, name, thickness):
        """
        Add a sediment layer with a constant thickness on all profiles
        @param name (str) name of the sediment layer
        @param thickness (float) layer thickness
        """
        self.has_layers = True
        self.nlayers += 1
        self.layer_names.append(name)
        for _, reach in self.reaches.items():
            for section in reach:
                thickness_table = [thickness for i in range(section.nb_points)]
                section.add_layer_from_thickness(thickness_table)

    def summary(self):
        """
        Method to print the summary of the MascaretGeoFile object
        """
        txt = '~> %s\n' % self
        for _, reach in self.reaches.items():
            txt += '    - %s\n' % reach
            for section in reach:
                txt += '        %i) %s\n' % (section.id, section)
        return txt


if __name__ == '__main__':
    # Parse every MascaretGeoFile in examples/mascaret and display a summary
    import os
    from utils.files import recursive_glob
    try:
        geo_files = recursive_glob(os.path.join(os.environ['HOMETEL'],
                                   'examples', 'mascaret'), '*.geo')
        geo_files += recursive_glob(os.path.join(os.environ['HOMETEL'],
                                    'examples', 'mascaret'), 'geometrie')
        for filename in sorted(geo_files):
            geo_file = MascaretGeoFile(filename, 'geo')
            print(geo_file.summary())
    except MascaretException as e:
        print(str(e))
