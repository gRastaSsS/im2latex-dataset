#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  latex2formulas.py
#  Parses tar files of latex files for formulas
#
#  © Copyright 2016, Anssi "Miffyli" Kanervisto
#  
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#  
import re
import tarfile
import os
import glob
import sys

PATTERNS = [r"\\begin\{equation\}(.*?)\\end\{equation\}",
            r"\$\$(.*?)\$\$",
            r"\$(.*?)\$",
            r"\\\[(.*?)\\\]",
            r"\\\((.*?)\\\)"]
DIR = ""

# Number of bytes required for formula to be saved
MIN_LENGTH = 40
MAX_LENGTH = 1024


def get_formulas(latex):
    """ Returns detected latex formulas from given latex string
    Returns list of formula strings"""
    final_result = []
    final_result_mod = []
    for pattern in PATTERNS:
        result = re.findall(pattern, latex, re.DOTALL)
        # Remove short ones
        result = [x.strip().replace("\n", "").replace("\r", "") for x in result if
                  MAX_LENGTH > len(x.strip()) > MIN_LENGTH]
        result_mod = [re.sub('\\label{.*}', '', x) for x in result]
        final_result.extend(result)
        final_result_mod.extend(result_mod)

    return final_result, final_result_mod


def main(directory):
    latex_tars = glob.glob(directory + "*.tar.gz")
    formulas = []
    formulas_mod = []
    ctr = 0
    for filename in latex_tars:
        tar = tarfile.open(filename)
        # List latex files
        files = tar.getnames()
        # Loop over and extract results
        for latex_name in files:
            if not "/" in latex_name:  # .getnames() includes directory-only
                continue
            tar.extract(latex_name)
            latex = open(latex_name).read()
            final_result, final_result_mod = get_formulas(latex)
            formulas.extend(final_result)
            formulas_mod.extend(final_result_mod)
            os.remove(latex_name)

        ctr += 1
        print("Done {} of {}".format(ctr, len(latex_tars)))
    formulas = list(set(formulas))
    print("Parsed {} formulas".format(len(formulas)))
    print("Saving formulas...")

    with open("formulas.txt", "w") as f:
        f.write("\n".join(formulas))

    with open("formulas-mod.txt", "w") as f:
        f.write("\n".join(formulas_mod))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("usage: latex2formulas tar_directory\n" +
              "tar_directory should hold .tar files containing latex sources")
    else:
        main(sys.argv[1])
