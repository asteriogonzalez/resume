#!/usr/bin/env python

import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

NAME = os.path.split(os.path.abspath('.'))[-1]
SHORT_NAME = NAME.lower().split('-')[-1]
MODULE_NAME = NAME.replace('-', '_')
VERSION = '0.13'
KEYWORDS = ['testing', 'pytest', 'long_run', SHORT_NAME]

setup(
    name=NAME,
    license='MIT',
    # packages=[NAME],
    version=VERSION,
    description="Save/Restore interpreter running state to resume interruped computations",
    author='Asterio Gonzalez',
    author_email='asterio.gonzalez@gmail.com',
    url='https://github.com/asteriogonzalez/{0}'.format(NAME),
    # download_url = \
    # 'https://github.com/asteriogonzalez/{0}/archive/{1}.tar.gz'\
    # .format(NAME, VERSION)
    keywords = KEYWORDS,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Topic :: Software Development :: Testing',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
    ],

    long_description=read("README.md"),
    py_modules=[MODULE_NAME],
    entry_points={'pytest11': ['{0} = {1}'.format(SHORT_NAME, MODULE_NAME)]},
    install_requires=['numpy']
)
