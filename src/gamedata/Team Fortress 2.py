import os
import subprocess
import pathlib


def extract(config, args, gameconfig):
    # this binary is missing from some linux installs of TF2
    # also no idea what the windows equivalent is
    # maybe switch to a dependency on https://github.com/ValvePython/vpk ?
    if not os.path.isfile(gameconfig.game_folder / "bin" / "vpk_linux32"):
        return
    os.makedirs(gameconfig.output_game_path / "sound" / "music", exist_ok = args.overwrite)
    accumulate_outputs = subprocess.CompletedProcess([], 0)
    archive_list_output = subprocess.run(
        [
            gameconfig.game_folder / "bin" / "vpk_linux32",
            "L",
            gameconfig.game_folder / "hl2" / "hl2_sound_misc_dir.vpk",
        ],
        env={"LD_LIBRARY_PATH": (gameconfig.game_folder / "bin")},
        capture_output=True,
        text=True,
    )
    file_list = [
        pathlib.Path(line.split()[0])
        for line in archive_list_output.stdout.split("\n")
        if len(line) > 0 and line[0]
    ]
    accumulate_outputs = archive_list_output
    accumulate_outputs.args = []
    for file in file_list:
        if file.match("sound/music/*"):
            archive_extract_output = subprocess.run(
                [
                    gameconfig.game_folder / "bin" / "vpk_linux32",
                    "x",
                    gameconfig.game_folder / "hl2" / "hl2_sound_misc_dir.vpk",
                    file,
                ],
                env={"LD_LIBRARY_PATH": (gameconfig.game_folder / "bin")},
                cwd=gameconfig.output_game_path,
                capture_output=True,
                text=True,
            )
            accumulate_outputs.stdout += archive_extract_output.stdout
            accumulate_outputs.stderr += archive_extract_output.stderr
            accumulate_outputs.returncode = max(
                archive_extract_output.returncode, accumulate_outputs.returncode
            )
            accumulate_outputs.args.append(str(file))
            os.rename(
                gameconfig.output_game_path / file, gameconfig.output_game_path / file.name
            )
    os.removedirs(gameconfig.output_game_path / "sound" / "music")
    return accumulate_outputs
