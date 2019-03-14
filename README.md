# VGM Extractor

A tool for extracting music files from installed video games.

While many game developers publish soundtrack albums with or separately from their games, many do not. This tool is meant to fill that gap, by providing the data and tooling necessary to extract the music from a game that is installed.

## Usage

    vgm-extractor.py [-h] --outputpath OUTPUTPATH --steamappspath
                     STEAMAPPSPATH [--format FORMAT]
                     [game [game ...]]

Example:

    vgm-extractor.py --outputpath ~/Music --steamappspath ~/.local/share/Steam/steamapps --format flac
