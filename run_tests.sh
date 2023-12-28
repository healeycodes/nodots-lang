#!/bin/bash
set -e

echo python3 --version
pip3 install -r requirements.txt
python3 -m mypy cli.py interpreter.py grammar.py
python3 tests.py
