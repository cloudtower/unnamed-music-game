#!/bin/bash

# build tex
python3 build.py $1 $2
# compile tex
pdflatex $2 > /dev/null
# remove build files
rm -r *.aux *.log pics/*
# remove intermediate song downloads
rm songs/*_uncut.mp3