from pathlib import Path
import pkgutil
import yaml

def load():
    game_data = {}
    script_dir = Path(__file__).resolve().parent
    for data_file_path in script_dir.glob("gamedata/*.yaml"):
        with open(data_file_path, "r") as data_file:
            game_data[data_file_path.stem] = yaml.safe_load(data_file.read())

    # TODO replace deprecated find_module and load_module
    for finder, name, ispkg in pkgutil.iter_modules(["gamedata"]):
        game_data[name]["python"] = finder.find_module(name).load_module()
    
    return game_data
