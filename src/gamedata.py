from pathlib import Path
import pkgutil
import yaml

def load():
    game_data = {}
    script_dir = Path(__file__).resolve().parent
    for data_file_path in script_dir.glob("gamedata/*.yaml"):
        name = data_file_path.stem
        with open(data_file_path, "r") as data_file:
            game_data[name] = yaml.safe_load(data_file.read())
            game_data[name].setdefault("game_name", name)
            game_data[name].setdefault("game_folder", name)

    # TODO replace deprecated find_module and load_module
    for finder, name, ispkg in pkgutil.iter_modules(["gamedata"]):
        game_data[name]["python"] = finder.find_module(name).load_module()
    
    return game_data
