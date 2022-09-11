#!/usr/bin/env python3

import fnmatch
from importlib.resources import path
import os
import shutil
import subprocess

from pathlib import Path
from zipfile import ZipFile

from UnityPy.enums.ClassIDType import ClassIDType

import args
import config
import file_util
import gamedata
import game_config
import steps
import unity_extract

parsed_args = args.parse()

game_data = gamedata.load()

configuration = config.Config(parsed_args, game_data)

# TODO: instead of looping through all the games we support, instead
# loop through the steampath itchpath programfiles etc
for game_name in configuration.games:
    if game_name not in game_data:
        raise FileNotFoundError
    game_configuration = game_config.GameConfig(configuration, parsed_args, game_name, game_data[game_name])
    if not game_configuration.game_folder:
        continue
    if game_configuration.output_game_path.exists() and not parsed_args.rescan:
        continue
    Path(game_configuration.output_game_path).mkdir(exist_ok=True)
    if parsed_args.verbose > 0:
        print(game_name)
    for step in game_data[game_name]["extract_steps"]:
        # The type of extraction step is identified by one or more unique keys

        # filespec indicates we are going to copy some files and folders
        if "filespec" in step:
            steps.FilespecStep(step).execute(configuration, parsed_args, game_configuration)

        # python contains a python script to run to extract music somehow
        elif "python" in step:
            steps.PythonStep(step).execute(configuration, parsed_args, game_configuration)

        # tag_filespec describes the output files to be tagged
        if "tag_filespec" in step:
            # tag files from the script
            for filepath in game_configuration.output_game_path.glob(step["tag_filespec"]):
                file_util.tag(filepath, game_name, parsed_args.albumsuffix)

        # zip files
        if "zipfile" in step:
            with ZipFile(
                Path(game_configuration.game_folder.joinpath(step["zipfile"])), "r"
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
                                or not game_configuration.output_game_path.joinpath(filename).exists()
                            ):
                                found_files = True
                                zipfile.extract(filename, path=game_configuration.output_game_path)
                                file_util.tag(game_configuration.output_game_path / filename, game_name, parsed_args.albumsuffix)
                                (game_configuration.output_game_path / filename).rename(
                                    game_configuration.output_game_path / Path(filename).name
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
                    game_configuration.output_game_path,
                    "-b",
                    game_configuration.game_folder.joinpath(step["xsb_file"]),
                    str(step.get("xsb_offset", 0)),
                    game_configuration.game_folder.joinpath(step["xwb_file"]),
                ],
                stdin=yes.stdout,
            )
            yes.stdout.close()

        # Unity assets files
        if "assetsfile" in step:
            assetsfilespec = step.get("assetsfilespec", None)
            assetsexcludespec = step.get("assetsexcludespec", None)
            if not isinstance(assetsfilespec, list):
                assetsfilespec = [assetsfilespec]
            if not isinstance(assetsexcludespec, list):
                assetsexcludespec = [assetsexcludespec]
            def asset_filter(obj):
                if obj.type == ClassIDType.AudioClip:
                    if obj.m_Length and obj.m_Length < parsed_args.minduration:
                        return False
                    if obj.name:
                        # TODO sync with other multiple filespec behavior 
                        for excludespec in assetsexcludespec:
                            if excludespec and fnmatch.fnmatch(obj.name, excludespec):
                                return False
                        for filespec in assetsfilespec:
                            if filespec and fnmatch.fnmatch(obj.name, filespec):
                                # print("======", obj.name)
                                # for k in dir(obj):
                                #     print(k,str(getattr(obj,k))[:100])
                                return True
                        return False
                    return True
                return False
            # print(game_configuration.game_folder.joinpath(step["assetsfile"]), game_configuration.output_game_path)
            path_id_list = unity_extract.extract_assets(
                str(game_configuration.game_folder.joinpath(step["assetsfile"])),
                game_configuration.output_game_path,
                use_container = False,
                append_path_id = False,
                asset_filter = asset_filter,
            )
            if len(path_id_list) == 0:
                raise "Empty unity extract"
            # TODO collect and output filenames for verbose>1

    file_util.remove_empty_dir_tree(game_configuration.output_game_path)
