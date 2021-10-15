#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md')) as f:
    long_description = f.read()

setup(
    name='topopyscale',
    version='0.0.1',
    description='A Python package to perform statistical climate downscaling at the hillslope scale',
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/ArcticSnow/TopoPyScale',

    # Author details
    author=['Simon Filhol', 'Joel Fiddes', 'Kristoffer Aalstad'],
    author_email=['simon.filhol@geo.uio.no', 'joelfiddes@gmail.com', 'kristoffer.aalstad@geo.uio.no'],

    # Choose your license
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Visualization',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3.8',
    ],

    # What does your project relate to?
    keywords=['climate','downscaling', 'meteorology'],
    packages=find_packages(),
    install_requires=['matplotlib', 'scikit-learn', 'pandas', 'numpy', 'xarray', 'pvlib', 'topocalc', 'cdsapi', 'rasterio'],
    include_package_data=True
)
