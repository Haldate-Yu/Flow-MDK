#!/usr/bin/env python3
"""@author TELEMAC-MASCARET Consortium

   @brief Generation of compacted file from sources, configuration, examples
"""
import shutil
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from os import path, sep

from config import CFGS, add_config_argument, update_config
from utils.exceptions import TelemacException
from utils.files import create_directories, tel_zip
from utils.messages import git_banner


def main():
    """ Main function of compact_telemac.py """
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Reads config file ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    print('\n\nLoading Options and Configurations\n'+72*'~'+'\n')
    parser = ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter,
        description=('''\n\
Compact the TELEMAC system files, into various archived:\n
1. archiving sources if necessary
2. archiving examples if necessary
3. archiving binaries if necessary
4. ...
        '''),
        usage=' (--help for help)\n---------\n       =>'
              '  %(prog)s [options] \n---------')
    parser = add_config_argument(parser)
    parser.add_argument(
        "-a", "--archive-name", metavar="archive name",
        dest="archive_name", default='',
        help="specify the archive name, default is taken as the config name")
    parser.add_argument(
        "-m", "--modules", metavar="modules",
        dest="modules", default='',
        help="specify the list modules, default is taken from config file")
    parser.add_argument(
        "--src", action="store_true",
        dest="src_only", default=False,
        help="create a zip containing only the sources i.e. the "
             "bare minimum to use telemac-mascaret")
    parser.add_argument(
        "--examples", action="store_true",
        dest="examplesOnly", default=False,
        help="create a zip containing only the sources i.e. the "
             "bare minimum to use telemac-mascaret")
    options = parser.parse_args()

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Environment ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    update_config(options)
    root_dir = CFGS.get_root()

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ banners ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    version = CFGS.get_version()
    git_banner(root_dir, version=version)

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Works for only one common root and zipper ~~~~~~~~~~~~~~~~~~~
    CFGS.compute_zip_info()
    cfg = CFGS.configs[CFGS.cfgname]
    zip_ext = cfg['ZIPPER']

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ src_only is independent of config ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    if options.src_only:
        # ~~> create the archive directory
        if options.archive_name != '':
            archive_name = options.archive_name
        else:
            archive_name = 'otm_'+version+'-src'
        print('\n\nArchive ' + archive_name + '\n'+'~'*72+'\n')
        tmp_dir = path.join(root_dir, archive_name)
        if path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        create_directories(tmp_dir)
        # ~~> copy the content of the following dirs into the archive directory
        dirs = ['optionals', 'scripts', 'sources', 'documentation', 'configs']
        for pid in dirs:
            input_path = path.join(root_dir, pid)
            output_path = input_path.replace(root_dir, tmp_dir)
            shutil.copytree(input_path, output_path,
                     ignore=shutil.ignore_patterns('.git', '*.pyc'))
            print('    +> '+input_path)
        # ~~> copy the following files into the archive directory
        files = ['NEWS.txt', 'README.txt']
        for pid in files:
            input_path = path.join(root_dir, pid)
            output_path = input_path.replace(root_dir, tmp_dir)
            shutil.copy2(input_path, output_path)
            print('    +> '+input_path)
        # ~~> prepare an empty directory for future builds
        pid = path.join(root_dir, 'builds')
        output_path = pid.replace(root_dir, tmp_dir)
        create_directories(output_path)
        # ~~> zipping the archive directory
        print('\n... now packaging ' + archive_name)
        tel_zip(archive_name, tmp_dir, zip_ext)
        # ~~> cleaning the archive directory
        print('\n... now cleaning ')
        shutil.rmtree(tmp_dir)

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ examplesOnly is independent of config ~~~~~~~~~~~~~~~~~~~~~~~
    elif options.examplesOnly:
        # ~~> create the archive directory
        if options.archive_name != '':
            archive_name = options.archive_name
        else:
            archive_name = 'otm_'+version+'-examples'
        print('\n\nArchive ' + archive_name + '\n'+'~'*72+'\n')
        tmp_dir = path.join(root_dir, archive_name)
        if path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        create_directories(tmp_dir)
        # ~~> copy the content of the following dir into the archive directory
        dirs = ['examples']
        for pid in dirs:
            input_path = path.join(root_dir, pid)
            output_path = input_path.replace(root_dir, tmp_dir)
            shutil.copytree(input_path, output_path,
                     ignore=shutil.ignore_patterns('.git', '*.pyc'))
            print('    +> '+input_path)
        # ~~> zipping the archive directory
        print('\n... now packaging ' + archive_name)
        tel_zip(archive_name, tmp_dir, zip_ext)
        # ~~> cleaning the archive directory
        print('\n... now cleaning ')
        shutil.rmtree(tmp_dir)

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Works for all configurations unless specified ~~~~~~~~~~~~~~~
    else:
        for cfgname in CFGS.configs:
            if options.modules != '':
                cfg['modules'] = \
                    options.modules.replace(',', ' ')\
                                   .replace(';', ' ').replace('.', ' ')
            # parsing for proper naming
            CFGS.compute_compact_info()
            CFGS.light_dump()

    # ~~ Scans all source files to build a relation database ~~~~~~~~~~~
            if cfg['MODULES'] == {}:
                raise TelemacException(\
                        '\nNot able to find any modules within'
                        'your root directory {}\n'.format(cfg['root']))

            # ~~> create the archive directory
            if options.archive_name != '':
                archive_name = options.archive_name
            else:
                archive_name = 'otm_'+version+'-builds-'+cfgname
            print('\n\nArchive ' + archive_name + '\n'+'~'*72+'\n')
            tmp_dir = path.join(root_dir, archive_name)
            if path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
            create_directories(tmp_dir)
            # ~~> copy the content of the following dir
            # into the archive directory
            dirs = ['builds'+sep+cfgname, 'scripts', 'sources', 'configs']
            for pid in dirs:
                input_path = path.join(root_dir, pid)
                output_path = input_path.replace(root_dir, tmp_dir)
                shutil.copytree(input_path, output_path,
                         ignore=shutil.ignore_patterns('.git', '*.pyc'))
                print('    +> '+input_path)
            # ~~> zipping the archive directory
            print('\n... now packaging ' + cfgname)
            tel_zip(cfgname, tmp_dir, cfg['ZIPPER'])
            # ~~> cleaning the archive directory
            print('\n... now cleaning ')
            shutil.rmtree(tmp_dir)

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
# ~~~~ Success message ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    print('\n\nMy work is done\n\n')

    sys.exit(0)


if __name__ == "__main__":
    main()
