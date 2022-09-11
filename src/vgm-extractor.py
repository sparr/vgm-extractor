#!/usr/bin/env python3

import fnmatch
from importlib.resources import path
import shutil

from pathlib import Path

import args
import config
import file_util
import gamedata
import game_config
import steps

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
        elif "tag_filespec" in step:
            # tag files from the script
            for filepath in game_configuration.output_game_path.glob(step["tag_filespec"]):
                file_util.tag(filepath, game_name, parsed_args.albumsuffix)

        # zip files
        elif "zipfile" in step:
            steps.ZipfileStep(step).execute(configuration, parsed_args, game_configuration)

        # xwb files
        elif "xwb_file" in step and "xsb_file" in step and shutil.which("unxwb"):
            steps.XwbfileStep(step).execute(configuration, parsed_args, game_configuration)

        # Unity assets files
        if "assetsfile" in step:
            steps.AssetsfileStep(step).execute(configuration, parsed_args, game_configuration)

    file_util.remove_empty_dir_tree(game_configuration.output_game_path)
