#!/bin/bash

set -ex
python setup.py vendor
python setup.py sdist
python setup.py package
ls -lh dist
