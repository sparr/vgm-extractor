import fnmatch
import subprocess

from pathlib import Path
from UnityPy.enums.ClassIDType import ClassIDType
from zipfile import ZipFile

import file_util
import unity_extract

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
            self.step["filespec"] = self.step["filespec"][0]
        for filepath in gameconfig.game_folder.glob(self.step["filespec"]):
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
            found_files = False
            zipfilespec = self.step["zipfilespec"]
            if not zipfilespec:
                zipfilespec = ["*"]
            else:
                if isinstance(zipfilespec, str):
                    zipfilespec = [zipfilespec]
            for spec in zipfilespec:
                for filename in zipfile.namelist():
                    if fnmatch.fnmatch(filename, spec):
                        if (
                            args.overwrite
                            or not gameconfig.output_game_path.joinpath(filename).exists()
                        ):
                            found_files = True
                            zipfile.extract(filename, path=gameconfig.output_game_path)
                            file_util.tag(gameconfig.output_game_path / filename, gameconfig.gamename, args.albumsuffix)
                            (gameconfig.output_game_path / filename).rename(
                                gameconfig.output_game_path / Path(filename).name
                            )
                            if args.verbose > 1:
                                print("  " + filename)
                if found_files:
                    break
        # TODO: eliminate unwanted levels of folder nesting here

# unxwb from https://aluigi.altervista.org/papers.htm#xbox
# TODO: support --overwrite
class XwbfileStep(Step):
    def execute(self, config, args, gameconfig):
        if args.overwrite:
            prompt_key = "y"
        else:
            prompt_key = "n"
        yes = subprocess.Popen(["yes", prompt_key], stdout=subprocess.PIPE)
        # TODO capture output, suppress based on verbosity
        unxwb = subprocess.run(
            [
                "unxwb",
                "-d",
                gameconfig.output_game_path,
                "-b",
                gameconfig.game_folder.joinpath(self.step["xsb_file"]),
                str(self.step.get("xsb_offset", 0)),
                gameconfig.game_folder.joinpath(self.step["xwb_file"]),
            ],
            stdin=yes.stdout,
        )
        yes.stdout.close()

class AssetsfileStep(Step):
    def execute(self, config, args, gameconfig):
        assetsfilespec = self.step.get("assetsfilespec", None)
        assetsexcludespec = self.step.get("assetsexcludespec", None)
        if not isinstance(assetsfilespec, list):
            assetsfilespec = [assetsfilespec]
        if not isinstance(assetsexcludespec, list):
            assetsexcludespec = [assetsexcludespec]
        def asset_filter(obj):
            if obj.type == ClassIDType.AudioClip:
                if obj.m_Length and obj.m_Length < args.minduration:
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
        # print(config.game_folder.joinpath(step["assetsfile"]), config.output_game_path)
        path_id_list = unity_extract.extract_assets(
            str(gameconfig.game_folder.joinpath(self.step["assetsfile"])),
            gameconfig.output_game_path,
            use_container = False,
            append_path_id = False,
            asset_filter = asset_filter,
        )
        if len(path_id_list) == 0:
            raise "Empty unity extract"
        # TODO collect and output filenames for verbose>1