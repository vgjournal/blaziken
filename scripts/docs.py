"""
Script to generate the project's documentation.
Pass the '--modules' flag to generate .rst documents for each module in the library's package.

Useful Links:

* `Sphinx docs <https://www.sphinx-doc.org/en/master/>`_
* `Sphinx rst docs <https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html>`_
* `Sphinx docstrings directives <https://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html>`_
* `Sphinx rst markup reference <https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html>`_
* `Extension autodoc-typehints <https://github.com/agronholm/sphinx-autodoc-typehints>`_
"""
from pathlib import Path
from subprocess import CompletedProcess
from subprocess import run
from sys import argv
from sys import stdout
from webbrowser import open_new_tab


MODULES_ARG = '--modules'
SHOW_ARG = '--show'


def main() -> CompletedProcess:
    """ Builds the documentation. """
    project_root = Path(__file__).absolute().parent.parent
    if MODULES_ARG in argv:
        run([
            'sphinx-apidoc',
            str(project_root / 'blaziken'),
            '--output-dir', str(project_root / 'docs' / 'source' / 'modules'),
            '--separate',
            '--no-toc',
            '--module-first',
            '--ext-autodoc',
        ], check=False)
    result = run([
        str( project_root / 'docs' / 'make.bat'),
        'html',
    ], check=False)
    if SHOW_ARG in argv:
        open_new_tab(str(project_root / 'docs' / 'build'/ 'html'/ 'index.html'))
    else:
        stdout.write('\nTo automatically open the generated HTML documentation,  '
                     f'pass the {SHOW_ARG} option to this script.\n')
    return result


if __name__ == '__main__':
    main()
