# VGM Extractor

A tool for extracting music files from installed video games.

While many game developers publish soundtrack albums with or separately from their games, many do not. This tool is meant to fill that gap, by providing the data and tooling necessary to extract the music from a game that is installed.

VGM Extractor contains a [database](src/gamedata) of games describing where and how their music is stored. For games with bare music files, it copies them. For other games, it orchestrates other format-specific [tools](#third-party-tools)

## Usage

    vgm-extractor.py [-h] [-v[v...]] --outputpath OUTPUTPATH
                     [--steamlibrarypath STEAMLIBRARYPATH]
                     [--albumsuffix ALBUMSUFFIX] [--format FORMAT]
                     [--overwrite] [--rescan] [--minduration MINDURATION]
                     [game [game ...]]

Example:

    vgm-extractor.py --outputpath ~/Music --steamlibrarypath ~/Games --format flac

## Prerequisites

### Python

This script requires some python modules described in the [Pipfile](Pipfile), which you can install via `pipenv install` or `pip install -r $(pipenv requirements)`

### Third Party Tools

Specific tools must be on the path to extract certain types of archives:

- [unxwb](https://github.com/mariodon/unxwb) for XACT Wave Bank `.xwb` files
- [quickbms](http://aluigi.altervista.org/quickbms.htm) for a variety of formats
- [icoextract](https://github.com/jlu5/icoextract) to extract icons from exe files
- [ffmpeg](http://www.ffmpeg.org/) or [libav](http://libav.org/) for converting wav files to other audio formats

## Contributing

At present we can only extract from about 110 games, installed via Steam. Adding support for additional games ranges from easy (no programming at all, just list the file locaitons) to difficult depending on the game. Adding support for other game publishing platforms, operating systems, etc is a more involved undertaking. PRs are welcome!

## Game Data

[src/gamedata/README.md](src/gamedata/README.md) explains the contents of the game data files.
