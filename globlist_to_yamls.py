#!/usr/bin/env python3

"""Takes a list of glob patterns like SomeGame/foo/*mp3 and produces gamedata yaml files"""

from sys import stdin
from pathlib import Path
from yaml import dump

prev_game = ""
outfile = None
outdata = {}
for line in stdin:
    path = Path(line.strip())
    if str(path.parts[0]) != prev_game:
        if outdata:
            dump(outdata, outfile, explicit_start=True, sort_keys=False, indent=2)
        prev_game = str(path.parts[0])
        if outfile:
            outfile.close()
        outfile = open(prev_game + ".yaml", "w")
        outdata = {"game_name": prev_game, "game_folder": prev_game, "extract_steps": []}
    outdata["extract_steps"].append({"filespec":str(path.relative_to(path.parts[0]))})
if outfile:
    if outdata:
        dump(outdata, outfile, explicit_start=True, sort_keys=False, indent=2)
    outfile.close()