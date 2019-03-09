#!/usr/bin/env python3

import os
import glob
import yaml
import string
import shutil
import subprocess
import mutagen

#TODO specify games to process at command line
#GAMES=["Factorio","Nuclear Throne"]
GAMES=[]

#TODO specify formats at commend line
#TODO priority order of formats
#TODO all formats
# prefer mp3 if available
FORMAT="mp3"

#TODO split game data into separate files
with open("gamedata.yaml","r") as gamedatafile:
  gamedata = yaml.load(gamedatafile.read())

#TODO specify steam path at command line
#TODO detect steam path from steam config
steampath = "/home/sparr/.local/share/Steam/steamapps/common"

#TODO specify output path at command line
vgmpath = "/home/sparr/Media/Music/VGM"

#apply id3/ogg/etc album tag to file
def tag(file, gamename):
  mutafile = mutagen.File(file, easy=True)
  if mutafile is not None:
    #TODO handle ID3 Frame types for non-Easy classes
    if 'album' not in mutafile:
      mutafile['album'] = gamename
    mutafile.save()

def copy(src, dst):
  shutil.copy(src, dst)

def copy_and_tag(src, dst, gamename):
  copy(src, dst)
  if os.path.isdir(dst):
    dst = os.path.join(dst, os.path.basename(src))
  tag(dst, gamename)

for gamename, data in gamedata.items():
  # only process games in GAMES[] unless it's empty
  if len(GAMES)>0 and gamename not in GAMES:
    continue
  # replace / with _ to make valid directory name
  copydst = os.path.join(vgmpath, gamename.replace("/","_"))
  if data:
    # game data contains a dict, keys are operating system names
    for opsys in data:
      # keys are platforms like steam/gog
      for platform in data[opsys]:
        #TODO: support more platforms than steam
        if platform != 'steam':
          continue
        apppath = os.path.join(steampath, data[opsys][platform]['appname'])
        if not os.path.isdir(apppath):
          continue
        try:
          os.mkdir(copydst)
        except FileExistsError:
          pass
        print(gamename)
        # musicpaths specify places to find music files
        if 'musicpaths' in data[opsys][platform]:
          for musicpath in data[opsys][platform]['musicpaths']:
            # dict of paths to multiple formats of the same music
            if 'formats' in musicpath:
              if FORMAT in musicpath['formats']:
                musicpath.update(musicpath['formats'][FORMAT])
              else:
                musicpath.update(musicpath['formats'].values()[0])
            for filepath in glob.glob(os.path.join(apppath, musicpath['path'], musicpath['filespec'])):
              copy_and_tag(filepath, copydst, gamename)
            if musicpath.get('recurse', False):
              for filepath in glob.glob(os.path.join(apppath, musicpath['path'], '**', musicpath['filespec']), recursive=True):
                relpath = os.path.relpath(filepath, os.path.join(apppath, musicpath['path']))
                newpath = os.path.join(copydst, relpath)
                try:
                  os.makedirs(os.path.dirname(newpath))
                except FileExistsError:
                  pass
                copy_and_tag(filepath, newpath, gamename)
            if 'coverspec' in musicpath:
              for filepath in glob.glob(os.path.join(apppath, musicpath['path'], musicpath['coverspec'])):
                copy(filepath, copydst)
        # script contains a bash script to run to extract music somehow
        if 'script' in data[opsys][platform]:
          subprocess.run(["bash", "-c", string.Template(data[opsys][platform]['script']).substitute(apppath=apppath,copydst=copydst)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
          if 'script_filespec' in data[opsys][platform]:
            # tag files from the script
            for filepath in glob.glob(os.path.join(copydst, data[opsys][platform]['script_filespec'])):
              tag(filepath, gamename)