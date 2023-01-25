#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

PYTHONPATH="${PYTHONPATH}:${SCRIPT_DIR}"

echo "Now PYTHONPATH is $PYTHONPATH in this console. You can start work with geocoder."

export PYTHONPATH

