import fnmatch
import os
import subprocess

from pathlib import Path
from zipfile import ZipFile

import file_util

def apply_filespecs(filename, filespecs, excludespecs = None):
    if not isinstance(filespecs, list):
        filespecs = [filespecs]
    if not isinstance(excludespecs, list):
        excludespecs = [excludespecs]
    for excludespec in excludespecs:
        if excludespec and fnmatch.fnmatch(filename, excludespec):
            return False
    for filespec in filespecs:
        if filespec and fnmatch.fnmatch(filename, filespec):
            return True
    return False


class Step():
    def __init__(self, step):
        self.step = step
    def execute(self):
        pass

class FilespecStep(Step):
    def execute(self, config, args, gameconfig):
        if isinstance(self.step["filespec"], list):
            if args.format == "*":
                # we want all formats
                # keep the whole filespec list
                pass
            else:
                self.step["filespec"] = [
                    spec
                    for spec in self.step["filespec"]
                    if Path(spec).suffix[1:].lower() == args.format.lower()
                    and next(gameconfig.game_folder.glob(spec))
                ]
            if len(self.step["filespec"]) == 0:
                return False
            # FIXME improve spec to implement both of these needs:
            # filespec list might be [a/*.mp3,b/*.mp3] and we want the first that matches
            # filespec list might be [a/*.ogg,b/*.mp3] and we want the first that we can get
            # filespec list might be [a/*.ogg,b/*.mp3] and we want either or both depending on args.format
            # TODO support multiple args.format
            filespecs = self.step["filespec"]
        else:
            filespecs = [self.step["filespec"]]
        for filespec in filespecs:
            for filepath in gameconfig.game_folder.glob(filespec):
                copydst = gameconfig.output_game_path
                strip_glob_path = self.step.get("strip_glob_path", "")
                if strip_glob_path != "":
                    strip_glob_full_path = gameconfig.game_folder.joinpath(strip_glob_path)
                    copydst = gameconfig.output_game_path.joinpath(
                        filepath.parent.relative_to(strip_glob_full_path)
                    )
                    copydst.mkdir(parents=True, exist_ok=True)
                try:
                    if file_util.audio_duration(filepath) >= args.minduration:
                        if args.verbose > 1:
                            print("  " + str(filepath.relative_to(gameconfig.game_folder)))
                        file_util.copy_and_tag(filepath, copydst, gameconfig.gamename, args.overwrite)
                except FileExistsError:
                    pass

class PythonStep(Step):
    def execute(self, config, args, gameconfig):
            python_output = getattr(config.gamedata[gameconfig.gamename]["python"], self.step["python"])(
                config, args, gameconfig
            )
            if python_output:
                if args.verbose > 2:
                    print(python_output.stdout, end="")
                    print(python_output.stderr, end="")
                if args.verbose > 1:
                    for file in python_output.args:
                        print("  " + file)

class ZipfileStep(Step):
    def execute(self, config, args, gameconfig):
        with ZipFile(
            Path(gameconfig.game_folder.joinpath(self.step["zipfile"])), "r"
        ) as zipfile:
            for filename in zipfile.namelist():
                if apply_filespecs(filename, self.step["zipfilespec"], self.step["zipexcludespec"]):
                    if (
                        args.overwrite
                        or not gameconfig.output_game_path.joinpath(filename).exists()
                    ):
                        zipfile.extract(filename, path=gameconfig.output_game_path)
                        file_util.tag(gameconfig.output_game_path / filename, gameconfig.gamename, args.albumsuffix)
                        (gameconfig.output_game_path / filename).rename(
                            gameconfig.output_game_path / Path(filename).name
                        )
                        if args.verbose > 1:
                            print("  " + filename)
        # TODO: eliminate unwanted levels of folder nesting here

# unxwb from https://github.com/mariodon/unxwb
# TODO: support --overwrite
class XwbfileStep(Step):
    def execute(self, config, args, gameconfig):
        if args.overwrite:
            prompt_key = "y"
        else:
            prompt_key = "n"
        yes = subprocess.Popen(["yes", prompt_key], stdout=subprocess.PIPE)
        # TODO capture output, suppress based on verbosity
        command = [
                "unxwb",
                "-d",
                gameconfig.output_game_path,
            ]
        if "xsb_file" in self.step:
            command.extend( [
                "-b",
                gameconfig.game_folder.joinpath(self.step["xsb_file"]),
                str(self.step.get("xsb_offset", 0)),
            ])
        command.append(gameconfig.game_folder.joinpath(self.step["xwb_file"]))
        unxwb = subprocess.run(
            command,
            stdin=yes.stdout,
        )
        yes.stdout.close()

class AssetsfileStep(Step):
    def execute(self, config, args, gameconfig):
        try:
            from UnityPy.enums.ClassIDType import ClassIDType
            from UnityPy.tools.extractor import extract_assets
        except:
            return
        # TODO support image assets to find album art
        # TODO support video assets for music videos and audio extraction
        def asset_filter(obj):
            if obj.type == ClassIDType.AudioClip:
                if obj.m_Length and obj.m_Length < args.minduration:
                    return False
                if obj.name:
                    return apply_filespecs(obj.name, self.step["assetsfilespec"], self.step.get("assetsexcludespec",None))
                return True
            return False
        # print(config.game_folder.joinpath(step["assetsfile"]), config.output_game_path)
        assetsfiles = self.step["assetsfile"]
        if not isinstance(assetsfiles, list):
            assetsfiles = [assetsfiles]
        for assetsfile in assetsfiles:
            path_id_list = extract_assets(
                str(gameconfig.game_folder.joinpath(assetsfile)),
                gameconfig.output_game_path,
                use_container = False,
                append_path_id = False,
                asset_filter = asset_filter,
            )
            if len(path_id_list) == 0:
                raise Exception("Empty unity extract")
        # TODO collect and output filenames for verbose>1

class QuickBmsStep(Step):
    def execute(self, config, args, gameconfig):
        if args.overwrite:
            overwrite = "-o"
        else:
            overwrite = "-k"
        # TODO capture output, suppress based on verbosity
        command = [
                "quickbms",
                overwrite,
            ]
        if "quickbmsfilespec" in self.step:
            filespecs = self.step["quickbmsfilespec"]
            if not isinstance(filespecs, list):
                filespecs = [filespecs]
            command.extend( [
                "-f",
                ";".join(filespecs)
            ])
        script_dir = Path(__file__).resolve().parent
        command.append(script_dir / "scripts" / self.step["quickbmsscript"])
        command.append(gameconfig.game_folder.joinpath(self.step["quickbmsarchive"]))
        command.append(gameconfig.output_game_path)
        # TODO consolidate use of subprocess (here, unxwb, etc) for consistent handling of output
        quickbms = subprocess.run(command)

class FilterFilespecStep(Step):
    def execute(self, config, args, gameconfig):
        for file in gameconfig.output_game_path.glob(self.step["filterfilespec"]):
            if not apply_filespecs(file, self.step.get("filterincludespec","*"), self.step.get("filterexcludespec",None)) or file_util.audio_duration(file) < args.minduration:
                os.unlink(file)

class FlattenFilespecStep(Step):
    def execute(self, config, args, gameconfig):
        dirs = set()
        for file in gameconfig.output_game_path.glob(self.step["flattenfilespec"]):
            if file.is_file():
                # TODO allow partial flattening
                print(file, gameconfig.output_game_path / file.name)
                os.rename(file, gameconfig.output_game_path / file.name)
            elif file.is_dir():
                dirs.add(file)
            else:
                # TODO handle sockets, block devices, etc?
                pass
        for dir in dirs:
            try:
                os.removedirs(dir)
            except FileNotFoundError:
                pass
