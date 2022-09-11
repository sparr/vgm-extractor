import argparse
from pathlib import Path
import vdf

from sys import platform
if platform.startswith("win"):
    import winreg


class Config:
    def __init__(self, args, gamedata):
        if not Path(args.outputpath).is_dir():
            args.parser.error("outputpath is not a directory")

        self.output_path = Path(args.outputpath)

        if args.steamlibrarypath:
            path = Path(args.steamlibrarypath)
            if not path.is_dir():
                args.parser.error("steamlibrarypath is not a directory")
            self.steam_library_paths = [path]
        else:
            self.steam_library_paths = []
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
                        self.steam_library_paths.append(path)
            # TODO fallback on config/config.vdf BaseInstallFolder_1
        if len(self.steam_library_paths) == 0:
            raise Exception(
                "Failed to locate any Steam library directory, use --steamlibrarypath argument instead"
            )
        
        self.gamedata = gamedata

        self.games = args.games
        if len(self.games) == 0:
            self.games = sorted(gamedata.keys())

        

