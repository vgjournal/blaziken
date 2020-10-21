"""
Installation module.
To install, use `pip install .` (cwd must be the same as this file).
To uninstall, use `pip uninstall blaziken`. The package name is the setup(name=) kwarg.
"""
# Built-in imports
from pathlib import Path
from setuptools import find_packages
from setuptools import setup
# Project imports
from blaziken import __author__
from blaziken import __description__
from blaziken import __email__
from blaziken import __url__
from blaziken import __version__


requirements_path = (Path(__file__).parent / 'requirements.txt').resolve()
with open(requirements_path, 'r') as req_file:
    requirements = req_file.read().splitlines()


setup(
    name='blaziken',
    version=__version__,
    author=__author__,
    author_email=__email__,
    url=__url__,
    description=__description__,
    packages=find_packages(),
    install_requires=requirements,
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Internet :: WWW/HTTP',
        'Typing :: Typed',
    ],

)
