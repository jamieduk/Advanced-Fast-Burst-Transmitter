#!/bin/bash
# (c) J~Net 2026
#
# ./setup.sh
#
#
#
if [ ! -f "venv/bin/activate" ]; then
    echo "Creating virtual environment..."
    #/usr/bin/rm -rf venv
    python -m venv venv
fi

source venv/bin/activate

echo "Virtual Environment Setup and ready!"


pip install -r requirements.txt
pip install reedsolo
