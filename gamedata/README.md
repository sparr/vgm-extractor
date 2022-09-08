# Game Data

Each yaml file in this directory corresponds to a single game.
Each py file is paired with the matching yaml file.

## File Names

File names should be capitalized consistent with the most common references to the game. Punctuation should be stripped unless it represents something other than punctuation in the name, or the name would be significantly less unique or recognizable without the punctuation. The full punctuated name of the game will be found inside the file.

## File Contents

### YAML Files

YAML files describe how to extract music from the game, using a variety of common tools such as file paths, extensions, archive extractors, etc. Additionally data may describe how to extract a suitable "cover art" image representing the game, as if the music were an album.

#### Data

* **game_name** *string* The full name of the game, suitable for metadata tagging
* **game_folder** *string* The name of the game directory under steamapps/common or Program Files or similar
* **extract_steps** *[]* Steps to be taken in order to extract music from the game folder
  * **filespec** *string or [string,...]* A glob pattern (like "music/*.mp3") of files to copy, or a list of patterns
  * **strip_glob_path** *string* Disable the default behavior of putting all the files in the same directory, stripping only the directory(s) specified in this option
  * **python** *string* The name of a function in the matching python module to be run
  * **tag_filespec** *string* A glob pattern of files to apply id3 album tags to based on the game name
  * **xwb_file** *string* XACT Wave Bank archive to be unpacked with unxwb
  * **xsb_file** *string* XACT Sound Bank archive containing file names for the matching XWB file
  * **xsb_offset** *int* Byte offset into the XSB file where file names start
  * **zipfile** *string* A zip file to be unzipped
  * **zipfilespec** *string or [string,...]* A glob pattern of files to extract from the zip file in the same step

### Python Files

Occasionally a game requires custom logic, and this will be found in the python file and referenced in the yaml file. See [Team Fortress 2](Team%20Fortress%202.py) for an example.

#### Functions

Each python file is loaded as a module, and should contain top level functions. Each function should take the following arguments:

* **output_game_path** *Path* path to the base folder where extracted files for this game should go
* **game_folder** *Path* path to the installed game folder
* **args** *{string:any}* parsed command line arguments from the original vgm-extractor invocation

Each function may return a subprocess.CompletedProcess
