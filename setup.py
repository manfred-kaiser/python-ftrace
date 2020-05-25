# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

# read the contents of your README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='ftrace',
    version='0.0.1',
    author='Manfred Kaiser',
    author_email='manfred.kaiser@logfile.at',
    description='library for reading ftrace data',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    python_requires='>= 3.5',
    packages=find_packages(),
    url="https://github.com/manfred-kaiser/python-ftrace",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Operating System :: POSIX :: Linux",
        "Topic :: System :: Operating System Kernels :: Linux"
    ],
)
