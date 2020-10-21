""" Script for running the arbitrary, mutable single test. """
from subprocess import run


run(['python', '-m', 'unittest', 'tests.test__single.SingleTest.test'], check=False)
