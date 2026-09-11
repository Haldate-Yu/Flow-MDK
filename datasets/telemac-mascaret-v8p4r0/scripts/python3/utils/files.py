"""
Toolbox providing several utility functions for file management.
"""
import codecs
import difflib
import errno
import os
import time
import zipfile
from fnmatch import filter
from pathlib import Path
from shutil import make_archive

from utils.progressbar import ProgressBar

# _____                  ___________________________________________
# ____/ General Toolbox /__________________________________________/
#

def check_sym_link(use_link):
    """
    Check if symbolic linking is available. Disabled on Windows because mlink
    requires UAC rights.

    @param use_link (boolean) option link instead of copy in the temporary
                              folder
    @return (boolean)
    """
    return os.name != 'nt' and use_link


def recursive_glob(treeroot, pattern):
    """
    Returns list of files matching pattern in all subdirectories of treeroot
    (to avoid usage of glob.glob with recursive argument which is not supported
     by Python >3.5)

    @param treeroot (str) Folder path
    @param pattern (str) Pattern to search for
    """
    results = []
    for base, _, files in os.walk(treeroot):
        goodfiles = filter(files, pattern)
        results.extend(os.path.join(base, f) for f in goodfiles)
    return results


def is_newer(source: str, target: str):
    """
    Check whether a file or directory is more recent than another one.

    @param file1 (str) First file or directory
    @param file2 (str) Second file or directory

    @return bool Return True if source exists and is more recent than
                 target, or if target does not exists, otherwise
                 False.
    """
    path1 = Path(source)
    path2 = Path(target)

    if not path1.exists():
        return False
    
    if not path2.exists():
        return True

    # Compare both timestamps
    if path1.stat().st_mtime > path2.stat().st_mtime:
        return True

    # If the first path is a directory, also compare its children
    if path1.is_dir():
        for child in os.listdir(source):
            if is_newer(child, target):
                return True

    return False


def get_file_content(fle):
    """
    Read fle file

    @param fle (string) file

    @return ilines (list) content line file
    """
    ilines = []
    src_file = codecs.open(fle, 'r', encoding='utf-8')
    for line in src_file:
        ilines.append(line)
    src_file.close()
    return ilines


def put_file_content(fle, lines):
    """
    put line to file

    @param fle (string) file
    @param lines (string) adding line
    """
    if os.path.exists(fle):
        os.remove(fle)
    src_file = open(fle, 'wb')
    if len(lines) > 0:
        ibar = 0
        pbar = ProgressBar(maxval=len(lines)).start()
        src_file.write(bytes((lines[0].rstrip()).replace('\r', '')
                                                .replace('\n\n', '\n'),
                             'utf-8'))
        for line in lines[1:]:
            pbar.update(ibar)
            ibar += 1
            src_file.write(bytes('\n'+(line.rstrip()).replace('\r', '')
                                                     .replace('\n\n', '\n'),
                                 'utf-8'))
        pbar.finish()
    src_file.close()


def add_file_content(fle, lines):
    """
    Add line to file

    @param fle (string) file
    @param lines (string) adding line
    """
    src_file = open(fle, 'ab')
    ibar = 0
    pbar = ProgressBar(maxval=len(lines)).start()
    for line in lines[0:]:
        ibar += 1
        pbar.update(ibar)
        src_file.write(bytes('\n'+(line.rstrip()).replace('\r', '')
                                                 .replace('\n\n', '\n'),
                             'utf-8'))
    pbar.finish()
    src_file.close()


def create_directories(p_o):
    """
    create  directories tree

    @param p_o (string) directory
    """
    p_r = p_o
    p_d = []
    while not os.path.isdir(p_r):
        p_d.append(os.path.basename(p_r))
        p_r = os.path.dirname(p_r)
    while p_d != []:
        p_r = os.path.join(p_r, p_d.pop())
        os.mkdir(p_r)


def symlink_file(src, dest):
    """ Copy a file to its destination
        @param src (string) source file
        @param dest (string) target file
    """
    # If link already exist overwrite it
    try:
        os.symlink(src, dest)
    except OSError as excpt:
        if excpt.errno == errno.EEXIST:
            os.remove(dest)
            os.symlink(src, dest)


# _____                  ___________________________________________
# ____/ Archive Toolbox /__________________________________________/
#


def tel_zip(zname, bname, format):
    """
    bname is the root directory to be archived --
    Return the name of the archive, zname, with its full path --
    form can be either 'zip', 'gztar' ... read from the config file

    @param zname (string) archive name
    @param bname (string) file or directory to archive
    @param format (string) archive format

    @return zipfile (string) name of the archive, zname, with its full path
    """
    cpath = os.getcwd()
    os.chdir(os.path.dirname(bname))
    zip_file = make_archive(zname, format, base_dir=os.path.basename(bname))
    os.chdir(cpath)
    return zip_file


def zipsortie(sortie):
    """
    zip files and remove virtually all of them !

    @param sortie (string) output to archive

    @return zname (string) name of the archive
    """
    head, tail = os.path.splitext(os.path.basename(sortie))
    zname = head + '.zip'
    if os.path.dirname(sortie) != '':
        for dirname, _, filenames in os.walk(os.path.dirname(sortie)):
            break
    else:
        for dirname, _, filenames in os.walk('.'):
            break
    cpath = os.getcwd()
    os.chdir(dirname)
    z = zipfile.ZipFile(zname, 'a', compression=zipfile.ZIP_DEFLATED,
                        allowZip64=True)
    for filename in filenames:
        if (head == filename[:len(head)] and
                tail == os.path.splitext(filename)[1]):
            z.write(filename)
            if filename != os.path.basename(sortie):
                os.remove(filename)
    os.chdir(cpath)
    return zname


# _____               ______________________________________________
# ____/ Diff Toolbox /_____________________________________________/



def diff_text_files(f_file, t_file, options):
    """
    Command line interface to provide diffs in four formats:

    * ndiff:    lists every line and highlights interline changes.
    * context:  highlights clusters of changes in a before/after format.
    * unified:  highlights clusters of changes in an inline format.
    * html:     generates side by side comparison with change highlights.

    @param f_file (string)
    @param t_file (string)
    @param options (string)

    @return (str)
    """
    # we're passing these as arguments to the diff function
    f_date = time.ctime(os.stat(f_file).st_mtime)
    t_date = time.ctime(os.stat(t_file).st_mtime)
    f_lines = get_file_content(f_file)
    t_lines = get_file_content(t_file)

    if options.unified:
        return difflib.unified_diff(f_lines, t_lines,
                                    f_file, t_file, f_date, t_date,
                                    n=options.ablines)
    if options.ndiff:
        return difflib.ndiff(f_lines, t_lines)
    if options.html:
        return difflib.HtmlDiff().make_file(f_lines, t_lines,
                                            f_file, t_file,
                                            context=options.context,
                                            numlines=options.ablines)
    return difflib.context_diff(f_lines, t_lines,
                                f_file, t_file, f_date, t_date,
                                n=options.ablines)
