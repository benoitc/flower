import os
from setuptools import setup, find_packages
import sys

py_version = sys.version_info[:2]

PY3 = py_version[0] == 3

if PY3:
    if py_version < (3, 2):
        raise RuntimeError('On Python 3, Flower requires Python 3.2 or better')
else:
    if py_version < (2, 6):
        raise RuntimeError('On Python 2, Flower requires Python 2.6 or better')


CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Topic :: Software Development :: Libraries']


# read long description
with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as f:
    long_description = f.read()

DATA_FILES = [
        ('flower', ["LICENSE", "MANIFEST.in", "NOTICE", "README.rst",
                        "THANKS", "UNLICENSE"])
        ]


setup(name='flower',
      version='0.1.0',
      description = 'collection of modules to build distributed and reliable concurrent systems',
      long_description = long_description,
      classifiers = CLASSIFIERS,
      license = 'BSD',
      url = 'http://github.com/benoitc/flower',
      packages=find_packages(),
      install_requires = ['pyuv', 'greenlet', 'six'],
      data_files = DATA_FILES)
