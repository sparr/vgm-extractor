#!/usr/bin/env python3

import copy
import yaml
import shutil
import string
import fnmatch
import mutagen
import argparse
import subprocess
import pathvalidate
from pathlib import Path
from zipfile import ZipFile

arg_parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)
arg_parser.add_argument("games", metavar="game", nargs="*", help="games to extract")
arg_parser.add_argument("--outputpath", help="path to output folder", required=True)
arg_parser.add_argument(
    "--steamappspath", help="path to steamapps folder", required=True
)
arg_parser.add_argument(
    "--albumsuffix",
    help="appended to the game name in the Album metadata for each track",
    default="[VGMX]",
)
# TODO priority order of formats
arg_parser.add_argument(
    "--format", help="preferred file format/extension, or '*' for all", default="mp3"
)
arg_parser.add_argument(
    "--scriptoutput",
    help="show script output",
    default=False,
    action="store_const",
    const=True,
)
arg_parser.add_argument(
    "--overwrite",
    help="overwrite existing files",
    default=False,
    action="store_const",
    const=True,
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
        albumtag = gamename
        if args.albumsuffix:
            albumtag += " " + args.albumsuffix
        # TODO handle ID3 Frame types for non-Easy classes
        if "album" not in mutafile:
            mutafile["album"] = albumtag
        mutafile.save()


def file_copy(src, dst):
    if Path(dst).is_dir():
        dst = Path(dst).joinpath(Path(src).name)
    if not args.overwrite and dst.exists():
        # do not overwrite existing files
        raise FileExistsError
    shutil.copy(src, dst)
    return dst


def copy_and_tag(src, dst, gamename):
    dst = file_copy(src, dst)
    file_tag(dst, gamename)


if len(args.games) == 0:
    args.games = gamedata.keys()

for gamename in args.games:
    if gamename not in gamedata:
        raise FileNotFoundError
    data = gamedata[gamename]
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

            # The type of extraction step is identified by one or more unique keys

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

            # TODO: support Windows alternative
            # script contains a bash script to run to extract music somehow
            if "script" in step:
                subprocess.run(
                    [
                        "bash",
                        "-c",
                        string.Template(step["script"]).substitute(
                            game_folder=game_folder, output_path=outputgamepath
                        ),
                    ],
                    stdout=None if args.scriptoutput else subprocess.DEVNULL,
                    stderr=None if args.scriptoutput else subprocess.DEVNULL,
                )

            # tag_filespec describes the output files to be tagged
            if "tag_filespec" in step:
                # tag files from the script
                for filepath in outputgamepath.glob(step["tag_filespec"]):
                    file_tag(filepath, gamename)

            # zip files
            if "zipfile" in step:
                with ZipFile(
                    Path(game_folder.joinpath(step["zipfile"])), "r"
                ) as zipfile:
                    for filename in zipfile.namelist():
                        if fnmatch.fnmatch(filename, step["zipfilespec"]):
                            if (
                                not args.overwrite
                                and outputgamepath.joinpath(filename).exists()
                            ):
                                # do not overwrite existing files
                                continue
                            zipfile.extract(filename, path=outputgamepath)
                            file_tag(outputgamepath.joinpath(filename), gamename)
                # TODO: eliminate unwanted levels of folder nesting here

            # xwb files
            # unxwb from https://aluigi.altervista.org/papers.htm#xbox
            # TODO: support --overwrite
            if "xwb_file" in step and "xsb_file" in step and shutil.which("unxwb"):
                no = subprocess.Popen(["yes", "n"], stdout=subprocess.PIPE)
                unxwb = subprocess.run(
                    [
                        "unxwb",
                        "-d",
                        outputgamepath,
                        "-b",
                        game_folder.joinpath(step["xsb_file"]),
                        str(step.get("xsb_offset", 0)),
                        game_folder.joinpath(step["xwb_file"]),
                    ],
                    stdin=no.stdout,
                )
                no.stdout.close()
