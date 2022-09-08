#!/usr/bin/env python3

import argparse
import copy
import fnmatch
import mutagen
import pathvalidate
import pkgutil
import shutil
import subprocess
import yaml
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
    "--pythonoutput",
    help="show python output",
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
arg_parser.add_argument(
    "--rescan",
    help="extract music for target directories that already exist",
    default=False,
    action="store_const",
    const=True,
)

args = arg_parser.parse_args()

if not Path(args.outputpath).is_dir():
    arg_parser.error("outputpath is not a directory")

output_path = Path(args.outputpath)

# TODO detect steam path from steam config
if args.steamappspath and not Path(args.steamappspath).is_dir():
    arg_parser.error("steamappspath is not a directory")

steamapps_path = Path(args.steamappspath).joinpath("common")

game_data = {}

script_dir = Path(__file__).resolve().parent
for data_file_path in script_dir.glob("gamedata/*.yaml"):
    with open(data_file_path, "r") as data_file:
        game_data[data_file_path.stem] = yaml.safe_load(data_file.read())

# TODO replace deprecated find_module and load_module
for finder, name, ispkg in pkgutil.iter_modules(["gamedata"]):
    game_data[name]["python"] = finder.find_module(name).load_module()

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
    args.games = game_data.keys()

# TODO: instead of looping through all the games we support, instead
# loop through the steampath itchpath programfiles etc
for game_name in args.games:
    if game_name not in game_data:
        raise FileNotFoundError
    data = game_data[game_name]
    # replace / with _ to make valid directory name
    output_game_path = output_path.joinpath(
        pathvalidate.sanitize_filename(game_name, "_")
    )
    if Path(output_game_path).exists() and not args.rescan:
        continue
    if data:
        # TODO: support more platforms than steam
        game_folder = steamapps_path.joinpath(data["game_folder"])
        if not game_folder.is_dir():
            continue
        Path(output_game_path).mkdir(exist_ok=True)
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
                            # FIXME: This is why the loop iteration has to use an index
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
                    copydst = output_game_path
                    if step.get("preserve_glob_directories", False):
                        filefolder = filepath.parent
                        copydst = output_game_path.joinpath(
                            filefolder.relative_to(
                                next(game_folder.glob(filespec)).parent
                            )
                        )
                        copydst.mkdir(parents=True, exist_ok=True)
                    try:
                        copy_and_tag(filepath, copydst, game_name)
                    except FileExistsError:
                        pass

            # python contains a python script to run to extract music somehow
            if "python" in step:
                python_output = getattr(data["python"], step["python"])(
                    {
                        "output_game_path": output_game_path,
                        "game_folder": game_folder,
                        "args": args,
                    }
                )
                if args.pythonoutput:
                    print(python_output.stdout, end="")
                    print(python_output.stderr, end="")

            # tag_filespec describes the output files to be tagged
            if "tag_filespec" in step:
                # tag files from the script
                for filepath in output_game_path.glob(step["tag_filespec"]):
                    file_tag(filepath, game_name)

            # zip files
            if "zipfile" in step:
                with ZipFile(
                    Path(game_folder.joinpath(step["zipfile"])), "r"
                ) as zipfile:
                    for filename in zipfile.namelist():
                        if fnmatch.fnmatch(filename, step["zipfilespec"]):
                            if (
                                not args.overwrite
                                and output_game_path.joinpath(filename).exists()
                            ):
                                # do not overwrite existing files
                                continue
                            zipfile.extract(filename, path=output_game_path)
                            file_tag(output_game_path.joinpath(filename), game_name)
                # TODO: eliminate unwanted levels of folder nesting here

            # xwb files
            # unxwb from https://aluigi.altervista.org/papers.htm#xbox
            # TODO: support --overwrite
            if "xwb_file" in step and "xsb_file" in step and shutil.which("unxwb"):
                if args.overwrite:
                    prompt_key = "y"
                else:
                    prompt_key = "n"
                yes = subprocess.Popen(["yes", prompt_key], stdout=subprocess.PIPE)
                unxwb = subprocess.run(
                    [
                        "unxwb",
                        "-d",
                        output_game_path,
                        "-b",
                        game_folder.joinpath(step["xsb_file"]),
                        str(step.get("xsb_offset", 0)),
                        game_folder.joinpath(step["xwb_file"]),
                    ],
                    stdin=yes.stdout,
                )
                yes.stdout.close()
