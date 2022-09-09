#!/usr/bin/env python3

import argparse
from cmath import inf
import copy
import fnmatch
import inspect ##FIXME TEMP
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
arg_parser.add_argument('-v', '--verbose', action='count', default=0)
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
arg_parser.add_argument(
    "--minduration",
    help="minimum duration in seconds of files to keep",
    type=int,
    default=60,
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
            try:
                mutafile["album"] = albumtag
            except:
                mutafile["album"] = mutagen.id3.TextFrame(encoding=3, text=[albumtag])
        mutafile.save()


def file_copy(src, dst):
    if Path(dst).is_dir():
        dst = Path(dst).joinpath(Path(src).name)
    if not args.overwrite and dst.exists():
        # do not overwrite existing files
        raise FileExistsError
    shutil.copy(src, dst)
    return dst

def file_duration(file):
    mutafile = mutagen.File(file, easy=True)
    if mutafile is not None:
        return mutafile.info.length
    else:
        return inf # unrecognized sound files and non sound files

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
    output_game_path = output_path / pathvalidate.sanitize_filename(game_name, "_")
    if output_game_path.exists() and not args.rescan:
        continue
    if data:
        # TODO: support more platforms than steam
        game_folders = data["game_folder"]
        if isinstance(game_folders, str):
            game_folders = [game_folders]
        found_game_folder = None
        for game_folder in game_folders:
            game_folder = steamapps_path.joinpath(game_folder)
            if game_folder.is_dir():
                found_game_folder = game_folder
                break
        if not found_game_folder:
            continue
        Path(output_game_path).mkdir(exist_ok=True)
        if args.verbose > 0:
            print(game_name)
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
                        # keep the whole filespec list
                        pass
                    else:
                        filespec = [spec for spec in filespec if Path(spec).suffix[1:].lower() == args.format.lower()]
                    if len(filespec) > 1:
                        # insert new steps, one for each additional filespec of the proper format
                        for newspec in filespec[::-1]:
                            newstep = copy.deepcopy(step)
                            newstep["filespec"] = newspec
                            # FIXME: This is why the loop iteration has to use an index
                            data["extract_steps"].insert(i + 1, newstep)
                    filespec = filespec[0]
                for filepath in game_folder.glob(filespec):
                    copydst = output_game_path
                    strip_glob_path = step.get("strip_glob_path", "")
                    if strip_glob_path != "":
                        strip_glob_full_path = game_folder.joinpath(strip_glob_path)
                        copydst = output_game_path.joinpath(filepath.parent.relative_to(strip_glob_full_path))
                        copydst.mkdir(parents=True, exist_ok=True)
                    try:
                        if file_duration(filepath) >= args.minduration:
                            if args.verbose > 1:
                                print("  " + str(filepath.relative_to(game_folder)))
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
                if python_output:
                    if args.verbose > 2:
                        print(python_output.stdout, end="")
                        print(python_output.stderr, end="")
                    if args.verbose > 1:
                        for file in python_output.args:
                            print("  " + file)

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
        try:
            output_game_path.rmdir()
        except:
            pass

