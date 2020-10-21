""" Script for running the arbitrary, mutable single test. """
from subprocess import run
from os import chdir
from pathlib import Path

chdir(Path(__file__).parent.parent.resolve())

run(['pylint', 'blaziken', '--output-format=colorized'], check=False)
