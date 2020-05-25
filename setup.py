# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


setup(
    name='ftrace',
    version='0.0.1',
    author='Manfred Kaiser',
    author_email='manfred.kaiser@logfile.at',
    description='library for reading ftrace data',
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
