#!/bin/bash
set -e

echo python3 --version
pip3 install -r requirements.txt
# TODO fix types
# python3 -m mypy cli.py interpreter.py grammar.py
python3 tests.py
