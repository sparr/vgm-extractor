#!/usr/bin/env python3

import fnmatch
from importlib.resources import path
import shutil

import args
import config
import file_util
import gamedata
import game_config
import steps

from pathlib import Path
from pydub import AudioSegment

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
        for k,func in steps.StepFuncs.items():
            if k in step:
                func(step).execute(configuration, parsed_args, game_configuration)
    if parsed_args.convertwav:
        for path in game_configuration.output_game_path.glob("**/*.wav"):
            audio = AudioSegment.from_wav(path)
            audio.export(path.with_suffix("." + parsed_args.convertwav), format=parsed_args.convertwav)
            path.unlink()

    # TODO keep track of games that are found but produce no audio files
    file_util.remove_empty_dir_tree(game_configuration.output_game_path)
