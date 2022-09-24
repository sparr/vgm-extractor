# VGM Extractor

A tool for extracting music files from installed video games.

While many game developers publish soundtrack albums with or separately from their games, many do not. This tool is meant to fill that gap, by providing the data and tooling necessary to extract the music from a game that is installed.

## Usage

    vgm-extractor.py [-h] [-v[v...]] --outputpath OUTPUTPATH
                     [--steamlibrarypath STEAMLIBRARYPATH]
                     [--albumsuffix ALBUMSUFFIX] [--format FORMAT]
                     [--overwrite] [--rescan] [--minduration MINDURATION]
                     [game [game ...]]

Example:

    vgm-extractor.py --outputpath ~/Music --format flac

## Prerequisites

### Python

This script requires some python modules described in the [Pipfile](Pipfile), which you can install via `pipenv install` or `pip install -r $(pipenv requirements)`

### Third Party Tools

Specific tools must be on the path to extract certain types of archives:

- [unxwb](https://github.com/mariodon/unxwb) for XACT Wave Bank `.xwb` files
- [quickbms](http://aluigi.altervista.org/quickbms.htm) for a variety of formats

## Contributing

At present we can only extract from a small list of games, installed via Steam. Adding support for additional games ranges from easy (no programming at all) to difficult depending on the game. Adding support for other game publishing platforms, operating systems, etc is a more involved undertaking. PRs are welcome!

## Game Data

[gamedata/README.md](gamedata/README.md) explains the contents of the game data files.