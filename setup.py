#!/usr/bin/env python
from setuptools import setup
from os import path

setup(
    name='gpu-deploy',
    version='0.0.1',
    description='GPU management for nvidia-docker',
    author='Eric Y. Wang',
    author_email='eric.wang2@bcm.edu',
    py_modules=['gpu_deploy'],
    python_requires='<3'
)
