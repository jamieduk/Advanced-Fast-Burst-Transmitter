#!/bin/bash
# (c) J~Net 2026
#
# ./start.sh
#
#

text="Loading, Please Wait..."
color="\e[92m"

echo -e "$color$text"

if [ ! -f "venv/bin/activate" ]; then
    echo "Creating virtual environment..."
    #/usr/bin/rm -rf venv
    python -m venv venv
fi

source venv/bin/activate

clear

echo "Super Fast Advanced Burst Transmitter By (c) J~Net 2026"

python audioburst/main.py



