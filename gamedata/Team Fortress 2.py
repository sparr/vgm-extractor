import os
import subprocess
import pathlib


def extract(data):
    os.makedirs(data["output_game_path"] / "sound" / "music")
    accumulate_outputs = subprocess.CompletedProcess([], 0)
    archive_list_output = subprocess.run(
        [
            data["game_folder"] / "bin" / "vpk_linux32",
            "L",
            data["game_folder"] / "hl2" / "hl2_sound_misc_dir.vpk",
        ],
        env={"LD_LIBRARY_PATH": (data["game_folder"] / "bin")},
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
                    data["game_folder"] / "bin" / "vpk_linux32",
                    "x",
                    data["game_folder"] / "hl2" / "hl2_sound_misc_dir.vpk",
                    file,
                ],
                env={"LD_LIBRARY_PATH": (data["game_folder"] / "bin")},
                cwd=data["output_game_path"],
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
                data["output_game_path"] / file, data["output_game_path"] / file.name
            )
    os.removedirs(data["output_game_path"] / "sound" / "music")
    return accumulate_outputs
