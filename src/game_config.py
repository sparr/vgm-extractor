from pathlib import Path
import pathvalidate

class GameConfig():
    def __init__(self, config, args, gamename, gamedata):
        self.gamename = gamename
        # replace / with _ to make valid directory name
        self.output_game_path = Path(args.outputpath) / pathvalidate.sanitize_filename(gamename, "_")
        # TODO: support more platforms than steam
        game_folders = gamedata["game_folder"]
        if not isinstance(game_folders, list):
            game_folders = [game_folders]
        self.game_folder = None
        for steam_library_path in config.steam_library_paths:
            for game_folder in game_folders:
                game_folder = steam_library_path / "steamapps/common" / game_folder
                if game_folder.is_dir():
                    self.game_folder = game_folder
                    break
            if self.game_folder:
                break
