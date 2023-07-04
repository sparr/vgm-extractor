# Game Data

Each yaml file in this directory corresponds to a single game.
Each py file is paired with the matching yaml file.

## File Names

File names should be capitalized consistent with the most common references to the game. Punctuation should be stripped unless it represents something other than punctuation in the name, or the name would be significantly less unique or recognizable without the punctuation. When it differs, the full punctuated name of the game will be found inside the file.

## File Contents

### YAML Files

YAML files describe how to extract music from the game, using a variety of common tools such as file paths, extensions, archive extractors, etc. Additionally data may describe how to extract a suitable "cover art" image representing the game, as if the music were an album.

#### Data

* **game_name** *string* The full name of the game, suitable for metadata tagging. Optional, defaults to filename
* **game_folder** *string* The name of the game directory under steamapps/common or Program Files or similar. Optional, defaults to filename
* **extract_steps** *[]* Steps to be taken in order to extract music from the game folder
  * **filespec** *string or [string,...]* A glob pattern (like "music/*.mp3") of files to copy, or a list of patterns from which only the first one with matches will be used
  * **strip_glob_path** *string* Disable the default behavior of putting all the files in the same directory, stripping only the directory(s) specified in this option
  * **python** *string* The name of a function in the matching python module to be run
  * **tag_filespec** *string* A glob pattern of files to apply id3 album tags to based on the game name
  * **xwb_file** *string* XACT Wave Bank archive to be unpacked with unxwb
  * **xsb_file** *string* XACT Sound Bank archive containing file names for the matching XWB file
  * **xsb_offset** *int* Byte offset into the XSB file where file names start
  * **zipfile** *string* A zip file to be unzipped
  * **zipfilespec** *string or [string,...]* A glob pattern of files to extract from the zip file in the same step, or a list of patterns

All paths in gamedata are relative to the `game_folder`, so you don't have to specify it repeatedly in fields like `zipfile` or `filespec`.

### Python Files

Occasionally a game requires custom logic, and this will be found in the python file and referenced in the yaml file. See [Team Fortress 2](Team%20Fortress%202.py) for an example.

#### Functions

Each python file is loaded as a module, and should contain top level functions. Each function should take the following arguments:

* **output_game_path** *Path* path to the base folder where extracted files for this game should go
* **game_folder** *Path* path to the installed game folder
* **args** *{string:any}* parsed command line arguments from the original vgm-extractor invocation

Each function may return a subprocess.CompletedProcess

## Tips

This section is meant to help you find music files in games so you can create and share new gamedata files.

### General

Regardless of how the music is stored, you'll probably eventually be looking at some labels or names of some sort. Here are some keywords you might search for if the list is too long to read thoroughly:

* "Soundtrack" and "OST" are almost always exactly what we're looking for
* "Music" is usually what we're looking for
* "ogg" and "mp3" file extensions are music more often than short sound effects
* "wav" file extensions are short sound effects more often than music
* "mus" and "bgm" are common prefixes or suffixes for music files
* "amb" is hit or miss, some games use it exclusively for music, others for more "background noise" things like water or traffic or static
* "intro" is often musical, but also often short

Music files are often much larger than sound effect files. For a compressed format like `ogg` or `mp3` a short sound effect might be a few kilobytes, while a music file that is a minute or longer will be at least a few hundred kilobytes, likely multiple megabytes. For an uncompressed format like `wav` the ratios are similar but everything is larger.

### Unity Assets

A unity `.assets` file will be handled by an `extract_steps` entry with at least an `assetsfile` field pointing to the `.assets` file, and possibly an `assetsfilespec` and/or `assetsexcludexpec` to limit the files extracted from the assets file.

There are many GUI and CLI tools available for exploring assets files (Unity Asset Explorer, Asset Ripper, UnityPy, etc). Choose one that works in your OS and is comfortable for you. Extract or browse the `AudioClip` assets in one or more `.assets` files and look for some combination of large sizes and/or relevant asset names (see [general tips](#general)). Once you've found the relevant files, you can create a new file describing them. Look at other game data files containing `assetsfile` for examples.

#### Example

Here are the steps I might take for the game Slipways:
```
$ cd steamapps/common/Slipways
$ ls *.assets
globalgamemanagers.assets  resources.assets  sharedassets0.assets  sharedassets1.assets  sharedassets2.assets  sharedassets3.assets
$ AssetRipper -o /tmp/assets --logFile /tmp/AssetRipper.log -v -q sharedassets0.assets
[long output listing every asset, but no AudioClip assets]
$ AssetRipper -o /tmp/assets --logFile /tmp/AssetRipper.log -v -q resources.assets
[long output listing every asset]
$ cd /tmp/assets/ExportedProject/Assets/AudioClip/
$ ls -lSr
[list of AudioClip assets and metadata files]
[look for keywords, listen to some, confirm which are the real music files]
[discover that Music_* are the right files]
$ cd
$ rm -rf /tmp/assets
```

Then I created [Slipways.yaml](Slipways.yaml) describing these findings.