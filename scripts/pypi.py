# Generating distribution packages and uploading to pypi

# https://packaging.python.org/tutorials/packaging-projects/
# python -m pip install --user --upgrade setuptools wheel
# python setup.py sdist bdist_wheel
# python -m twine upload --repository testpypi dist/*  # Upload to pypi test
# python -m twine twine upload dist/*  # Upload to production pypi
# python -m pip install --index-url https://test.pypi.org/simple/ blaziken  # Install from pypi test
