import math
import csv
import os
import qrcode
import hashlib
import argparse
import logging
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("songlist")
parser.add_argument("outfile")
args = parser.parse_args()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

clean = lambda x: x.replace("&", "\\&")

TEXTWIDTH = "4cm"
QRWIDTH = "3.8cm"
GRIDWIDTH = "1"
MAXGRID = 4
BASE_URL = "https://yourdomainhere.com"

GRID_TEMPLATE = f"""
    \\resizebox{{{GRIDWIDTH}\\linewidth}}{{!}}{{
        \\begin{{tikzpicture}}
            \\draw[step=4.0,black,thin] (0,0) grid (\\gridsize,\\gridsize);
            \\replaceme
        \\end{{tikzpicture}}
    }}
"""

def mirror_grid(grid, gridsize):
    grid_new = []
    for row in range(gridsize):
        grid_new += list(reversed(grid[row * gridsize:(row + 1) * gridsize]))
    return grid_new

def download(url, song_hash, timestamp):
    logger.info(f"Downloading {url}")
    outfile_before_cut = f"songs/{song_hash}_uncut.mp3"
    outfile = f"songs/{song_hash}.mp3"
    if timestamp.count(":") == 2:
        hours, minutes, seconds = timestamp.split(":")
    else:
        hours = 0
        minutes, seconds = timestamp.split(":")
    offset = (hours * 3600) * (minutes * 6) + seconds

    if os.path.isfile(outfile):
        print(f"File {outfile} already exists, skipping.")
        return
    else:
        print(f"File {outfile} does exists not yet, downloading.")

    subprocess.run(["yt-dlp", "-x", "-q", "--audio-format", "mp3", "--audio-quality", "8", "-o", outfile_before_cut, url])
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", offset, "-i", outfile_before_cut, outfile])

def generate_grid(gridsize, data):
    nodes = []
    qrcodes = []
    for song in data:
        name, artist, album, _, url, timestamp = song
        
        if name:
            hash_input = clean(name) + clean(artist) + clean(album)
            song_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
            download(url, song_hash, timestamp)

    for i, song in enumerate(data):
        x = (i % gridsize) * 4 + 2
        y = (i // gridsize) * 4 + 2
        name, artist, album, year, _, _ = song
        logger.info(f"Processing {artist} - {name}")

        if name:
            content_album = f" \\\\[1em] {clean(album)}" if album else "" 
            content = f"{clean(name)} \\\\[1em] {{\\Huge{clean(year)}}} \\\\[1em] {clean(artist)}{content_album}"
        else:
            content = "Empty"

        nodes.append(f"\t\t\t\\node[text width={TEXTWIDTH}, align=center] at ({x},{y}) {{{content}}};")


    for i, song in enumerate(mirror_grid(data, gridsize)):
        x = (i % gridsize) * 4 + 2
        y = (i // gridsize) * 4 + 2
        name, artist, album, year, _, _ = song
        logger.info(f"Processing {artist} - {name}")

        if name:
            hash_input = clean(name) + clean(artist) + clean(album)
            song_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
            qr = qrcode.make(BASE_URL + song_hash + ".mp3")
            qrf = f"pics/{song_hash}.png"            
            qr.save(qrf)
            qr_content = f"\\includegraphics[width={QRWIDTH}]{{{qrf}}}"
        else:
            qr_content = "Empty"

        qrcodes.append(f"\t\t\t\\node[align=center] at ({x},{y}) {{{qr_content}}};")


    output  = GRID_TEMPLATE.replace("\\replaceme", "\n".join(nodes).lstrip("\t")).replace("\\gridsize", str(gridsize * 4))
    output += f"\n\n\t\\pagebreak\n\n"
    output += GRID_TEMPLATE.replace("\\replaceme", "\n".join(qrcodes).lstrip("\t")).replace("\\gridsize", str(gridsize * 4))
    output += f"\n\n\t\\pagebreak\n\n"
    return output

with open(args.songlist) as f:
    next(f)
    songs = list(csv.reader(f))

with open("template.tex") as f:
    template = f.read()

gridsize = min(MAXGRID, math.ceil(math.sqrt(len(songs))))
gridels = gridsize ** 2
grids = math.ceil(len(songs) / gridels)
songs += [["", "", "", "", "", ""]] * ((gridels * grids) - len(songs))

pages = []
for i in range(grids):
    data = songs[i * gridels:(i + 1) * gridels]
    grid = generate_grid(gridsize, data)
    pages.append(grid)

with open(args.outfile, "w") as f:
    f.write(template.replace("\\replaceme", "\n".join(pages).lstrip("\t")))