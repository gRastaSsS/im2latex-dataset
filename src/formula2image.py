#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  formula2image.py
#  Turns bunch of formulas into images and dataset listing
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

"""
Purpose of this script is to turn list of tex formulas into images
and a dataset list for OpenAI im2latex task.
Script outputs two lists:
    - im2latex.lst
        - Each row is: [idx of formula] [image name] [render type]
            - idx of formula is the line number in im2latex_formulas.lst
            - image name is name of the image (without filetype) 
            - render type is name of the method used to draw the picture
              (See RENDERING_SETUPS)
    - im2latex_formulas.lst
        - List of formulas, one per line
            -> No \n characters in formulas (doesn't affect math tex)
"""

import glob
import os
import sys
import hashlib
import multiprocessing
from subprocess import call
from datetime import datetime
from random import shuffle

MAX_IMAGES = 300 * 1000
PRINT_PROGRESS_STEP = MAX_IMAGES / 10000
THREADS = multiprocessing.cpu_count() * 2 + 1
IMAGE_DIR = "formula_images"
DATASET_FILE = "im2latex.lst"
NEW_FORMULA_FILE = "im2latex_formulas.lst"
DEVNULL = open(os.devnull, "w")
BASIC_SKELETON = r"""
\documentclass[12pt]{article}
\pagestyle{empty}
\usepackage{amsmath}
\begin{document}

\begin{displaymath}
%s
\end{displaymath}

\end{document}
"""


def formula_to_image(formula):
    try:
        name = hashlib.sha1(formula.encode('utf-8')).hexdigest()[:20]
    except Exception:
        return None

    if os.path.isfile(name + ".png"):
        return None

    full_name = name + "_basic"

    formula = formula.strip("%")

    latex_str = BASIC_SKELETON % formula

    with open(full_name + ".tex", "w") as f:
        f.write(latex_str)

    # Turn .tex into .pdf
    code = call(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "%s.tex" % full_name], stdout=DEVNULL,
                stderr=DEVNULL)
    if code != 0:
        # print '.tex --> .pdf error'
        os.system("rm -rf " + full_name + "*")
        return None

    # Turn .pdf into .png
    code = call(["pdftoppm", "%s.pdf" % full_name, full_name, "-png", "-singlefile"], stdout=DEVNULL,
                stderr=DEVNULL)
    if code != 0:
        # print '.pdf --> .png error, code=%d' % code
        os.system("rm -rf " + full_name + "*")
        return None

    resulted_images = glob.glob(full_name + "-*")

    if len(resulted_images) > 1:
        # print 'Too many images error'
        for filename in resulted_images:
            os.system("rm -rf " + filename + "*")
        return None
    else:
        return [[full_name, "basic"]]


def main(formula_list):
    formulas = open(formula_list).read().split("\n")
    shuffle(formulas)
    formulas = formulas[:MAX_IMAGES]

    try:
        os.mkdir(IMAGE_DIR)
    except OSError as e:
        pass  # except because throws OSError if dir exists

    print("Number of threads: " + str(THREADS))
    print("Turning formulas into images...")

    # Change to image dir because textogif doesn't seem to work otherwise...
    oldcwd = os.getcwd()
    # Check we are not in image dir yet (avoid exceptions)
    if not IMAGE_DIR in os.getcwd():
        os.chdir(IMAGE_DIR)

    start_time = datetime.now()

    i = 0
    failed = 0
    names = []
    pool = multiprocessing.Pool(THREADS)
    for result in pool.imap(formula_to_image, formulas):
        names.append(result)

        i += 1
        if result is None:
            failed += 1
        if i % PRINT_PROGRESS_STEP == 0:
            print str(i) + " out of " + str(MAX_IMAGES) + " processed, " + str(failed) + " failed!"

    print(datetime.now() - start_time)

    print("Deleting temporary files...")
    os.system("rm -rf *.aux")
    os.system("rm -rf *.log")
    os.system("rm -rf *.pdf")
    os.system("rm -rf *.tex")

    print("Writing to .lst files...")

    os.chdir(oldcwd)

    zipped = list(zip(formulas, names))

    new_dataset_lines = []
    new_formulas = []
    ctr = 0
    for formula in zipped:
        if formula[1] is None:
            continue
        for rendering_setup in formula[1]:
            new_dataset_lines.append(str(ctr) + " " + " ".join(rendering_setup))
        new_formulas.append(formula[0])
        ctr += 1

    with open(NEW_FORMULA_FILE, "w") as f:
        f.write("\n".join(new_formulas))

    with open(DATASET_FILE, "w") as f:
        f.write("\n".join(new_dataset_lines))


def check_validity(dataset_file, formula_file, formula_dir):
    """ Checks if lists are valid, ie. no files missing etc """
    dataset_lines = open(dataset_file).read().split("\n")
    formula_file = open(formula_file).read().split("\n")
    formula_images = os.listdir(formula_dir)
    max_id = 0
    missing_files = 0

    for line in dataset_lines:
        if line == "":
            continue
        splt = line.split(" ")
        max_id = splt[0]
        if not splt[1] + ".png" in formula_images:
            missing_files += 1

    if int(max_id) + 1 != len(formula_file):
        print("Max id in dataset != formula_file length (%d vs %d)" %
              (int(max_id), len(formula_file)))

    print("%d files missing" % missing_files)


if __name__ == '__main__':
    if len(sys.argv) != 2 and len(sys.argv) != 4:
        print("To generate datasets:           formula2image.py formulalist\n" +
              "To validate generated datasets: " +
              "formula2image.py dataset_list formula_list formula_dir")
    elif len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        check_validity(sys.argv[1], sys.argv[2], sys.argv[3])
