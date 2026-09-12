#!/usr/bin/env python3
"""@author TELEMAC-MASCARET CONSORTIUM

   @brief Check syntax of Fortran code
"""

import re
import subprocess
import sys
from collections import OrderedDict
from os import path, walk

from config import CFGS

INVALID_COMMENT = re.compile(r'^[^!\n0-9#\ ]')
INDENT = re.compile(r'^(\ ){6}([ ]{2})*[ ][^\ ]')
CONTINUATION = re.compile(r'^(\ ){5}[^\&\ ]')
LOWERCASE = re.compile(r"^[^!#\"'\'']*[azertyuiopqsdfghjklmnbvcxw]")
LINETOOLONG = re.compile(r'^[^!]{73,}')
INVALID_CHARACTER = re.compile(r'\t|\r')
ENCODING = re.compile(r'.*charset=(?P<charset>[-a-zA-Z0-9]+)$')

REGEXS = [("invalid comment", INVALID_COMMENT),
          ("indent", INDENT),
          ("continuation symbol", CONTINUATION),
          ("lower case", LOWERCASE),
          ("line too long", LINETOOLONG),
          ("invalid character", INVALID_CHARACTER),
         ]

IGNORES_MODULES = ["mascaret", "nestor"]

def check_regex(regex, content):
    """
    Check for invalid characters

    @params regex Regular expression to check for
    @params content Content of the file to check

    @returns list List of tuple containing the number of the line and the line
    """
    errors = []
    for iline, line in enumerate(content):
        proc = re.match(regex, line.strip('\n'))
        if proc:
            errors.append((iline, line))
    return errors

def check_encoding(ffile):
    """
    Check that they are no files with encoding that does not support utf8
    This function only works onTrue linux

    @params ffile Name of the file to check

    @returns string, string each string correspond to the encoding and the the
    presence of windows newline The strings are empty if it is ok
    """
    encoding = ""
    win_nl = ""
    if sys.platform.startswith('win'):
        return encoding, win_nl

    # Checking charset using file command
    cmd = f"file -i {ffile}"
    tmp = subprocess.check_output(cmd, shell=True)
    encoding = tmp.decode('utf-8')
    proc = re.match(ENCODING, encoding)
    if proc:
        charset = proc.group('charset')
        if charset in ["utf-8", "us-ascii", "en-ascii"]:
            encoding = ""

    # Checking if we have Windows newline using file
    cmd = f"file {ffile}"
    tmp = subprocess.check_output(cmd, shell=True)
    win_nl = tmp.decode('utf-8')
    if 'crlf' not in win_nl.lower():
        win_nl = ""

    return encoding, win_nl


def check_file(root, ffiles, code_errors):
    """
    Check coding convention for a file

    @params root path of file directory
    @params ffile name of the file

    """
    tel_root = CFGS.get_root()
    # modules to skip
    skip = False
    for ignored in IGNORES_MODULES:
        if ignored in path.relpath(root, tel_root):
            skip = True
    if skip:
        return
    # Checking files
    for ffile in ffiles:
        file_path = path.join(path.relpath(root, tel_root), ffile)
        if ffile.lower().endswith(".f"):
            with open(path.join(root, ffile)) as myfile:
                # check regex errors
                lines = myfile.readlines()
                for name, regex in REGEXS:
                    errors = check_regex(regex, lines)
                    for iline, line in errors:
                        code_errors[name].append(f"{file_path}:{iline}:{line}")
            encoding, win_nl = check_encoding(path.join(root, ffile))
            if encoding != "":
                code_errors["encoding"].append(encoding)
            if win_nl != "":
                code_errors["windows character"].append(win_nl)


def check_code():
    """ Apply check of convention on Fortran files """

    tel_root = CFGS.get_root()

    code_errors = OrderedDict()
    for name, _ in REGEXS:
        code_errors[name] = []
    code_errors["encoding"] = []
    code_errors["windows character"] = []


    # Checking source files
    print(" ~> Checking sources files")
    for root, _, ffiles in walk(path.join(tel_root, "sources")):
        check_file(root, ffiles, code_errors)

    # Checking examples files
    print(" ~> Checking user fortran in examples")
    for root, _, ffiles in walk(path.join(tel_root, "examples")):
        check_file(root, ffiles, code_errors)


    # Summary of the checks
    has_errors = False
    print("Error summary:")
    for cat, errors in code_errors.items():
        has_errors = has_errors or len(errors)>0
        print(f" ~> {len(errors)} {cat} errors")

    # Writing the logs
    with open("check_code.log", "w") as myfile:
        for cat, errors in code_errors.items():
            if len(errors) > 0:
                myfile.write(f" ~> {cat}\n")
                for error in errors:
                    myfile.write(error)

    if has_errors:
        print()
        print("Some errors were detected")
        print("See check_code.log for list of lines with errors")
        sys.exit(1)
    else:
        print(" Check code OK")
