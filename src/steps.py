from pathlib import Path

import file_util

class Step():
    def __init__(self, step):
        pass
    def execute(self):
        pass

class FilespecStep(Step):
    def __init__(self, step):
        self.step = step
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
    def __init__(self, step):
        self.step = step
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
