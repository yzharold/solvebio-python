[![Build Status](https://travis-ci.org/solvebio/solvebio-python.svg?branch=master)](http://travis-ci.org/solvebio/solvebio-python)


SolveBio Python Client
======================

This is the SolveBio Python package and command-line interface (CLI).
This module is tested against Python 2.7, 3.6, 3.7, 3.8, PyPy and PyPy3.

Developer documentation is available at [docs.solvebio.com](https://docs.solvebio.com). For more information about SolveBio visit [www.solvebio.com](https://www.solvebio.com).



Installation & Setup
--------------------

Install `solvebio` using `pip`:

    pip install solvebio


For interactive use, we recommend installing `IPython` and `gnureadline`:

    pip install ipython
    pip install gnureadline


To log in, type:

    solvebio login


Enter your SolveBio credentials and you should be good to go!


Install from Git
----------------

    pip install -e git+https://github.com/solvebio/solvebio-python.git#egg=solve


Development
-----------

    git clone https://github.com/solvebio/solvebio-python.git
    cd solve-python/
    python setup.py develop

To run tests use `nosetest`:

    nosetests solvebio.test.test_dataset


Or install `tox` and run:

    pip install tox
    tox


Releasing
---------

Maintainers can release solvebio-python to PyPI with the following steps:


    # Bump the version and update the changelog
    bumpversion <major|minor|patch>
    git push --tags
    github_changelog_generator

    # Build and release to PyPI
    find . -name '*.pyc' -delete
    rm -rf dist/*
    python setup.py clean
    python setup.py sdist bdist_wheel
    twine upload dist/*


You will need to [configure Twine](https://twine.readthedocs.io/en/latest/#installation) in order to push to PyPI.


Support
-------

Developer documentation is available at [docs.solvebio.com](https://docs.solvebio.com).

If you experience problems with this package, please [create a GitHub Issue](https://github.com/solvebio/solvebio-python/issues).

For all other requests, please [email SolveBio Support](mailto:support@solvebio.com).
