#!/bin/bash
set -e

echo python3 --version
pip3 install -r requirements.txt
python3 -m mypy .
python3 tests.py
