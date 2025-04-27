#!/bin/bash

python3 build.py $1 $2
pdflatex $2 > /dev/null
rm -r *.aux *.log pics/*
rm songs/*_uncut.mp3