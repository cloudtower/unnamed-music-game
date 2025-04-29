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

# Very incomplete filter such that pdflatex doesn't hang
clean = lambda x: x.replace("&", "\\&")

# Constants, adapt if needed
TEXTWIDTH = "4cm"
QRWIDTH = "3.8cm"
GRIDWIDTH = "1"
MAXGRID = 4
# Adapt to wherever you host the mp3s here
BASE_URL = "https://yourdomainhere.com"


# Template for tikz picture
# Scale equally in both dimension so that it fits the page width
GRID_TEMPLATE = f"""
    \\resizebox{{{GRIDWIDTH}\\linewidth}}{{!}}{{
        \\begin{{tikzpicture}}
            \\draw[step=4.0,black,thin] (0,0) grid (\\gridsize,\\gridsize);
            \\replaceme
        \\end{{tikzpicture}}
    }}
"""


# Get the position of an element in the grid
# depending on the index and grid size
def get_grid_pos(index, gridsize):
    x = (index % gridsize) * 4 + 2
    y = (index // gridsize) * 4 + 2
    return x, y


# Generate a song hash from title, artist and album (should be unique)
def get_song_hash(title, artist, album):
    hash_input = clean(title) + clean(artist) + clean(album)
    return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()


# Mirror a grid on the vertical axis for
# long-side double-sided printing
def mirror_grid(grid, gridsize):
    grid_new = []
    for row in range(gridsize):
        grid_new += list(reversed(grid[row * gridsize:(row + 1) * gridsize]))
    return grid_new


# Download songs via yt-dlp and cut to required length with ffmpeg
def download(url, song_hash, timestamp):
    logger.debug(f"Downloading {url}")
    
    outfile_before_cut = f"songs/{song_hash}_uncut.mp3"
    outfile = f"songs/{song_hash}.mp3"
    
    # Process timestamp for cutting off intro of downloaded song
    if timestamp.count(":") == 2:
        # HH:MM:SS format, e.g. for cutting from a mix
        hours, minutes, seconds = timestamp.split(":")
    else:
        # MM:SS format
        hours = 0
        minutes, seconds = timestamp.split(":")
    # Calculate offset in seconds
    offset = (hours * 3600) * (minutes * 6) + seconds

    # Skip if file was already downloaded
    if os.path.isfile(outfile):
        logger.debug(f"File {outfile} already exists, skipping.")
        return
    else:
        logger.info(f"File {outfile} does exists not yet, downloading.")

    # invoke yt-dlp (extract audio, quiet, mp3 with medium quality)
    subprocess.run(["yt-dlp", "-x", "-q", "--audio-format", "mp3", "--audio-quality", "8", "-o", outfile_before_cut, url])
    # cut quietly with ffmpeg with -ss seconds offset, write to final destination
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", offset, "-i", outfile_before_cut, outfile])


# Generate a grid (tikz-picture) with a certain grid size from
# a song list with a square number of elements
def generate_grid(gridsize, data):
    nodes = [] # tikz nodes with text
    qrcodes = [] # tikz nodes with qr code images
    
    # Generate text nodes for card front side
    for i, song in enumerate(data):
        x, y = get_grid_pos(i, gridsize)
        title, artist, album, year, _, _ = song
        logger.debug(f"Generating text node for {artist} - {title}")

        if title:
            # Print album name if available
            content_album = f" \\\\[1em] {clean(album)}" if album else ""
            # Generate contents for card
            content = f"{clean(title)} \\\\[1em] {{\\Huge{clean(year)}}} \\\\[1em] {clean(artist)}{content_album}"
        else: # Placeholder grid element
            content = "Empty"

        nodes.append(f"\t\t\t\\node[text width={TEXTWIDTH}, align=center] at ({x},{y}) {{{content}}};")

    # Generate QR code nodes for card backside
    # Grid is mirrored for double-sided printing
    for i, song in enumerate(mirror_grid(data, gridsize)):
        x, y = get_grid_pos(i, gridsize)
        title, artist, album, year, _, _ = song
        logger.info(f"Generating QR code node for {artist} - {title}")

        if title:
            # Generate a song hash for easier processing
            # and so that the player cannot read the title
            song_hash = get_song_hash(title, artist, album)
            
            # Make QR code and save it under pics/
            # Include saved filename in tikz node
            qr = qrcode.make(BASE_URL + song_hash + ".mp3")
            qrf = f"pics/{song_hash}.png"            
            qr.save(qrf)
            qr_content = f"\\includegraphics[width={QRWIDTH}]{{{qrf}}}"
        else: # Placeholder grid element
            qr_content = "Empty"

        qrcodes.append(f"\t\t\t\\node[align=center] at ({x},{y}) {{{qr_content}}};")


    # Place text and QR-code nodes in tikz-picture template string
    output  = GRID_TEMPLATE.replace("\\replaceme", "\n".join(nodes).lstrip("\t")).replace("\\gridsize", str(gridsize * 4))
    output += f"\n\n\t\\pagebreak\n\n"
    output += GRID_TEMPLATE.replace("\\replaceme", "\n".join(qrcodes).lstrip("\t")).replace("\\gridsize", str(gridsize * 4))
    output += f"\n\n\t\\pagebreak\n\n"
    return output


# Read song list
with open(args.songlist) as f:
    next(f)
    songs = list(csv.reader(f))

# Download all songs
for song in songs:
    title, artist, album, _, url, timestamp = song
    
    song_hash = get_song_hash(title, artist, album)
    download(url, song_hash, timestamp)

# Read LaTeX
with open("template.tex") as f:
    template = f.read()

# Calculate grid size for the amount of songs in the songlist
# Pad to a square number with empty elements
# Split into multiple grids if song number is larger than the
# maximum grid size
gridsize = min(MAXGRID, math.ceil(math.sqrt(len(songs))))
gridels = gridsize ** 2
grids = math.ceil(len(songs) / gridels) # amount of grids needed for song list
songs += [["", "", "", "", "", ""]] * ((gridels * grids) - len(songs))
logger.info(f"Generating {grids} grids with size {gridsize}x{gridsize}")

# Generate tikz grid for 
pages = []
for i in range(grids):
    data = songs[i * gridels:(i + 1) * gridels]
    grid = generate_grid(gridsize, data)
    pages.append(grid)

# Write to output tex file
with open(args.outfile, "w") as f:
    f.write(template.replace("\\replaceme", "\n".join(pages).lstrip("\t")))