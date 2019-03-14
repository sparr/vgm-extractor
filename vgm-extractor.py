#!/usr/bin/env python3

import copy
import yaml
import shutil
import string
import mutagen
import argparse
import subprocess
import pathvalidate
from pathlib import Path

# for development purposes
import sys
import pprint

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("games", metavar="game", nargs="*", help="games to extract")
arg_parser.add_argument("--outputpath", help="path to output folder", required=True)
arg_parser.add_argument(
    "--steamappspath", help="path to steamapps folder", required=True
)
# TODO priority order of formats
arg_parser.add_argument(
    "--format", help="preferred file format/extension, or '*' for all", default="mp3"
)

args = arg_parser.parse_args()

if not Path(args.outputpath).is_dir():
    arg_parser.error("outputpath is not a directory")

outputpath = Path(args.outputpath)

# TODO detect steam path from steam config
if args.steamappspath and not Path(args.steamappspath).is_dir():
    arg_parser.error("steamappspath is not a directory")

steamappspath = Path(args.steamappspath).joinpath("common")

gamedata = {}

scriptdir = Path(__file__).resolve().parent
for datafilepath in scriptdir.glob("gamedata/*.yaml"):
    with open(datafilepath, "r") as datafile:
        gamedata.update(yaml.safe_load(datafile.read()))


# apply id3/ogg/etc album tag to file
def file_tag(file, gamename):
    mutafile = mutagen.File(file, easy=True)
    if mutafile is not None:
        # TODO handle ID3 Frame types for non-Easy classes
        if "album" not in mutafile:
            mutafile["album"] = gamename
        mutafile.save()


def file_copy(src, dst):
    if Path(dst).is_dir():
        dst = Path(dst).joinpath(Path(src).name)
    if dst.exists():
        # do not overwrite existing files
        raise FileExistsError
    shutil.copy(src, dst)
    return dst


def copy_and_tag(src, dst, gamename):
    dst = file_copy(src, dst)
    file_tag(dst, gamename)


for gamename, data in gamedata.items():
    if len(args.games) > 0 and gamename not in args.games:
        continue
    # replace / with _ to make valid directory name
    outputgamepath = outputpath.joinpath(pathvalidate.sanitize_filename(gamename, "_"))
    if data:
        # TODO: support more platforms than steam
        game_folder = steamappspath.joinpath(data["game_folder"])
        if not game_folder.is_dir():
            continue
        Path(outputgamepath).mkdir(exist_ok=True)
        print(gamename)
        # FIXME: there must be a cleaner way to do this loop
        i = -1
        while i < len(data["extract_steps"]) - 1:
            i += 1
            step = data["extract_steps"][i]
            # filespec indicates we are going to copy some files and folders
            if "filespec" in step:
                filespec = step["filespec"]
                if isinstance(filespec, list):
                    if args.format == "*":
                        # we want all formats
                        # insert new steps, one for each format available
                        for newspec in filespec[::-1]:
                            newstep = copy.deepcopy(step)
                            newstep["filespec"] = newspec
                            data["extract_steps"].insert(i + 1, newstep)
                        continue
                    else:
                        # use the first filespec with the right extension
                        filespec = next(
                            (
                                spec
                                for spec in filespec
                                if Path(spec).suffix.lower() == args.format.lower()
                            ),
                            # or just use the first filespec
                            filespec[0],
                        )
                for filepath in game_folder.glob(filespec):
                    copydst = outputgamepath
                    if step.get("preserve_glob_directories", False):
                        filefolder = filepath.parent
                        copydst = outputgamepath.joinpath(
                            filefolder.relative_to(
                                next(game_folder.glob(filespec)).parent
                            )
                        )
                        copydst.mkdir(parents=True, exist_ok=True)
                    try:
                        copy_and_tag(filepath, copydst, gamename)
                    except FileExistsError:
                        pass

            # script contains a bash script to run to extract music somehow
            if "script" in step:
                subprocess.run(
                    [
                        "bash",
                        "-c",
                        string.Template(step["script"]).substitute(
                            game_folder=game_folder, copydst=copydst
                        ),
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                # script_filespec describes the script output files to be tagged
                if "script_filespec" in step:
                    # tag files from the script
                    for filepath in outputgamepath.glob(step["script_filespec"]):
                        tag(filepath, gamename)
