#!/usr/bin/env python3

import argparse
import copy
import fnmatch
import mutagen
import os
import pathvalidate
import pkgutil
import shutil
import subprocess
import vdf
import yaml

from pathlib import Path
from sys import platform
from zipfile import ZipFile

if platform.startswith("win"):
    import winreg

arg_parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)
arg_parser.add_argument("-v", "--verbose", action="count", default=0)
arg_parser.add_argument("games", metavar="game", nargs="*", help="games to extract")
arg_parser.add_argument(
    "-o", "--outputpath", help="path to output folder", required=True
)
arg_parser.add_argument(
    "--steamlibrarypath",
    help="path to steam library folder which contains steamapps/",
    required=False,
)
arg_parser.add_argument(
    "-a",
    "--albumsuffix",
    help="appended to the game name in the Album metadata for each track",
    default="[VGMX]",
)
# TODO priority order of formats
arg_parser.add_argument(
    "--format", help="preferred file format/extension, or '*' for all", default="*"
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
    default=30,
)

args = arg_parser.parse_args()

if not Path(args.outputpath).is_dir():
    arg_parser.error("outputpath is not a directory")

output_path = Path(args.outputpath)

if args.steamlibrarypath:
    path = Path(args.steamlibrarypath)
    if not path.is_dir():
        arg_parser.error("steamlibrarypath is not a directory")
    steam_library_paths = [path]
else:
    steam_library_paths = []
    if platform.startswith("win"):
        try:
            # 64 bit windows
            hkey = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\WOW6432Node\Valve\Steam"
            )
        except:
            try:
                # 32 bit windows
                hkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\Valve\Steam")
            except:
                raise Exception(
                    "failed to find Steam registry keys, use --steamapppath argument instead"
                )
        steam_install_path = Path(winreg.QueryValueEx(hkey, "InstallPath")[0])

    # TODO support mac, probably looking in ~/Library/Application Support/Steam
    else:
        # ~/.steam/steam is a symlink to the Steam installation directory
        steam_install_path = Path.home() / ".steam/steam"
    if not steam_install_path.is_dir():
        raise Exception(
            "Failed to locate Steam installation directory, use --steamlibrarypath argument instead"
        )

    with open(steam_install_path / "config/libraryfolders.vdf") as vdf_file:
        libraryfolders_vdf = vdf.parse(vdf_file)
    for k, v in libraryfolders_vdf["libraryfolders"].items():
        if k.isdigit():  # library folder entries have keys like "0" "1" etc
            path = Path(v["path"])
            if path.is_dir():
                steam_library_paths.append(path)
    # TODO fallback on config/config.vdf BaseInstallFolder_1

if len(steam_library_paths) == 0:
    raise Exception(
        "Failed to locate any Steam library directory, use --steamlibrarypath argument instead"
    )

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
    else:
        if not (Path(dst).parent.is_dir()):
            os.makedirs(Path(dst).parent, exist_ok=True)
    if not args.overwrite and dst.exists():
        # do not overwrite existing files
        raise FileExistsError
    shutil.copy(src, dst)
    return dst

def file_move(src, dst):
    if Path(dst).is_dir():
        dst = Path(dst).joinpath(Path(src).name)
    else:
        if not (Path(dst).parent.is_dir()):
            os.makedirs(Path(dst).parent, exist_ok=True)
    if not args.overwrite and dst.exists():
        # do not overwrite existing files
        raise FileExistsError
    shutil.move(src, dst)
    return dst


def file_duration(file):
    mutafile = mutagen.File(file, easy=True)
    if mutafile is not None:
        return mutafile.info.length
    else:
        return float("inf")  # unrecognized sound files and non sound files


def copy_and_tag(src, dst, gamename):
    dst = file_copy(src, dst)
    file_tag(dst, gamename)

def move_and_tag(src, dst, gamename):
    dst = file_move(src, dst)
    file_tag(dst, gamename)


def remove_empty_dir_tree(path):
    path = Path(path)
    for child in path.glob("*"):
        if child.is_dir():
            remove_empty_dir_tree(child)
            try:
                child.rmdir()
            except:
                pass
    try:
        path.rmdir()
    except:
        pass


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
        for steam_library_path in steam_library_paths:
            for game_folder in game_folders:
                game_folder = steam_library_path / "steamapps/common" / game_folder
                if game_folder.is_dir():
                    found_game_folder = game_folder
                    break
            if found_game_folder:
                break
        if not found_game_folder:
            continue
        Path(output_game_path).mkdir(exist_ok=True)
        if args.verbose > 0:
            print(game_name)
        for step in data["extract_steps"]:
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
                        filespec = [
                            spec
                            for spec in filespec
                            if Path(spec).suffix[1:].lower() == args.format.lower()
                            and next(game_folder.glob(spec))
                        ]
                    if len(filespec) == 0:
                        continue
                    # FIXME improve spec to implement both of these needs:
                    # filespec list might be [a/*.mp3,b/*.mp3] and we want the first that matches
                    # filespec list might be [a/*.ogg,b/*.mp3] and we want the first that we can get
                    # filespec list might be [a/*.ogg,b/*.mp3] and we want either or both depending on args.format
                    # TODO support multiple args.format
                    filespec = filespec[0]
                for filepath in game_folder.glob(filespec):
                    copydst = output_game_path
                    strip_glob_path = step.get("strip_glob_path", "")
                    if strip_glob_path != "":
                        strip_glob_full_path = game_folder.joinpath(strip_glob_path)
                        copydst = output_game_path.joinpath(
                            filepath.parent.relative_to(strip_glob_full_path)
                        )
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
                    found_files = False
                    zipfilespec = step["zipfilespec"]
                    if not zipfilespec:
                        zipfilespec = ["*"]
                    else:
                        if isinstance(zipfilespec, str):
                            zipfilespec = [zipfilespec]
                    for spec in zipfilespec:
                        for filename in zipfile.namelist():
                            if fnmatch.fnmatch(filename, spec):
                                if (
                                    args.overwrite
                                    or not output_game_path.joinpath(filename).exists()
                                ):
                                    found_files = True
                                    zipfile.extract(filename, path=output_game_path)
                                    file_tag(output_game_path / filename, game_name)
                                    (output_game_path / filename).rename(
                                        output_game_path / Path(filename).name
                                    )
                                    if args.verbose > 1:
                                        print("  " + filename)
                        if found_files:
                            break
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
                # TODO capture output, suppress based on verbosity
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

            # Unity assets files
            if "assetsfile" in step and shutil.which("AssetRipper"):
                # TODO capture output, suppress based on verbosity
                ripper = subprocess.run(
                    [
                        "AssetRipper",
                        "-q",
                        "-o",
                        output_game_path,
                        "--logFile",
                        output_game_path / "AssetRipper.log",
                        game_folder.joinpath(step["assetsfile"])
                    ]
                )
                assets_path = output_game_path / "ExportedProject" / "Assets"
                assetsfilespec = step.get("assetsfilespec", "*")
                assetsexcludespec = step.get("assetsexcludespec", "")
                if not isinstance(assetsfilespec, list):
                    assetsfilespec = [assetsfilespec]
                # TODO sync with other multiple filespec behavior 
                for filespec in assetsfilespec:
                    for filepath in assets_path.glob(filespec):
                        if not fnmatch.fnmatch(filepath.relative_to(assets_path), assetsexcludespec):
                            if file_duration(filepath) >= args.minduration:
                                # TODO optionally strip leading directories, make consistent between step types
                                copydst = output_game_path / filepath.relative_to(assets_path)
                                move_and_tag(filepath, copydst, game_name)
                shutil.rmtree(output_game_path / "ExportedProject")
                os.remove(output_game_path / "AssetRipper.log")
        remove_empty_dir_tree(output_game_path)
