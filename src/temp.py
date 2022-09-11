#!/usr/bin/env python3

import fnmatch
import os
import pathvalidate
import shutil
import subprocess

from pathlib import Path
from zipfile import ZipFile

import args
import config
import file_util
import gamedata

parsed_args = args.parse()

game_data = gamedata.load()

configuration = config.Config(parsed_args, game_data)

# TODO: instead of looping through all the games we support, instead
# loop through the steampath itchpath programfiles etc
for game_name in configuration.games:
    if game_name not in game_data:
        raise FileNotFoundError
    data = game_data[game_name]
    # replace / with _ to make valid directory name
    output_game_path = Path(parsed_args.outputpath) / pathvalidate.sanitize_filename(game_name, "_")
    if output_game_path.exists() and not parsed_args.rescan:
        continue
    if data:
        # TODO: support more platforms than steam
        game_folders = data["game_folder"]
        if isinstance(game_folders, str):
            game_folders = [game_folders]
        found_game_folder = None
        for steam_library_path in configuration.steam_library_paths:
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
        if parsed_args.verbose > 0:
            print(game_name)
        for step in data["extract_steps"]:
            # The type of extraction step is identified by one or more unique keys

            # filespec indicates we are going to copy some files and folders
            if "filespec" in step:
                filespec = step["filespec"]
                if isinstance(filespec, list):
                    if parsed_args.format == "*":
                        # we want all formats
                        # keep the whole filespec list
                        pass
                    else:
                        filespec = [
                            spec
                            for spec in filespec
                            if Path(spec).suffix[1:].lower() == parsed_args.format.lower()
                            and next(game_folder.glob(spec))
                        ]
                    if len(filespec) == 0:
                        continue
                    # FIXME improve spec to implement both of these needs:
                    # filespec list might be [a/*.mp3,b/*.mp3] and we want the first that matches
                    # filespec list might be [a/*.ogg,b/*.mp3] and we want the first that we can get
                    # filespec list might be [a/*.ogg,b/*.mp3] and we want either or both depending on parsed_args.format
                    # TODO support multiple parsed_args.format
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
                        if file_util.audio_duration(filepath) >= parsed_args.minduration:
                            if parsed_args.verbose > 1:
                                print("  " + str(filepath.relative_to(game_folder)))
                            file_util.copy_and_tag(filepath, copydst, game_name, parsed_args.overwrite)
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
                    if parsed_args.verbose > 2:
                        print(python_output.stdout, end="")
                        print(python_output.stderr, end="")
                    if parsed_args.verbose > 1:
                        for file in python_output.args:
                            print("  " + file)

            # tag_filespec describes the output files to be tagged
            if "tag_filespec" in step:
                # tag files from the script
                for filepath in output_game_path.glob(step["tag_filespec"]):
                    file_util.tag(filepath, game_name, parsed_args.albumsuffix)

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
                                    parsed_args.overwrite
                                    or not output_game_path.joinpath(filename).exists()
                                ):
                                    found_files = True
                                    zipfile.extract(filename, path=output_game_path)
                                    file_util.tag(output_game_path / filename, game_name, parsed_args.albumsuffix)
                                    (output_game_path / filename).rename(
                                        output_game_path / Path(filename).name
                                    )
                                    if parsed_args.verbose > 1:
                                        print("  " + filename)
                        if found_files:
                            break
                # TODO: eliminate unwanted levels of folder nesting here

            # xwb files
            # unxwb from https://aluigi.altervista.org/papers.htm#xbox
            # TODO: support --overwrite
            if "xwb_file" in step and "xsb_file" in step and shutil.which("unxwb"):
                if parsed_args.overwrite:
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
                            if file_util.audio_duration(filepath) >= parsed_args.minduration:
                                # TODO optionally strip leading directories, make consistent between step types
                                copydst = output_game_path / filepath.relative_to(assets_path)
                                file_util.move_and_tag(filepath, copydst, game_name, parsed_args.overwrite)
                shutil.rmtree(output_game_path / "ExportedProject")
                os.remove(output_game_path / "AssetRipper.log")
        file_util.remove_empty_dir_tree(output_game_path)
