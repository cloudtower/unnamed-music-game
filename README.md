# Unnamed Music Game

## Requirements

Please install the following dependencies:

- Python 3 with pip
- Some TeX distro (e.g. TeX Live)
- pdflatex
- ffmpeg

The Python dependencies can be installed via pip:

`pip install -r requirements.txt`

To access the songs via QR-Code they have to be either hosted publicly or accessible through the local network.
Adapt the variable `BASE_URL` in the `build.py` script accordingly, either setting it to a domain where you can host stuff or to the (preferably static) IP address of your device.
In the latter case you can make the songs accessible by running `python3 -m http.server` inside the `songs` subfolder.

## Running

Create some data set by using the template CSV file.
Download and build everything by running `./build.sh input-file output-file`.
