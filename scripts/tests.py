""" Script for running all the project's tests. """
from pathlib import Path
from subprocess import CompletedProcess
from subprocess import run
from sys import argv
from sys import stdout
from webbrowser import open_new_tab


COVERAGE_ARG = '--coverage'


def main() -> CompletedProcess:
    """ Executes all tests. """
    try:
        show_coverage = bool(argv.pop(argv.index(COVERAGE_ARG)))
    except ValueError:
        show_coverage = False
    result = run(['coverage', 'run', '-m', 'unittest', 'discover', '-s', 'tests'] + argv[1:],
                 check=False)
    if show_coverage:
        run(['coverage', 'html'], check=False)
        open_new_tab(str(Path(__file__).parent.parent / 'htmlcov' / 'index.html'))
    else:
        stdout.write('\nTo show the coverage report, type "coverage report" for text version or '
                     f'pass the {COVERAGE_ARG} option to this script for the HTML version. \n')
    return result


if __name__ == '__main__':
    main()
