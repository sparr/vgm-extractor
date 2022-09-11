import mutagen
import os
from pathlib import Path
import shutil

# apply id3/ogg/etc album tag to file
def tag(file, gamename, suffix = ""):
    mutafile = mutagen.File(file, easy=True)
    if mutafile is not None:
        albumtag = gamename
        albumtag += suffix
        # TODO handle ID3 Frame types for non-Easy classes
        if "album" not in mutafile:
            try:
                mutafile["album"] = albumtag
            except:
                mutafile["album"] = mutagen.id3.TextFrame(encoding=3, text=[albumtag])
        mutafile.save()


def file_func(func, src, dst, overwrite = False):
    if Path(dst).is_dir():
        dst = Path(dst).joinpath(Path(src).name)
    else:
        if not (Path(dst).parent.is_dir()):
            os.makedirs(Path(dst).parent, exist_ok=True)
    if not overwrite and dst.exists():
        # do not overwrite existing files
        raise FileExistsError
    func(src, dst)
    return dst

def copy(src, dst, overwrite = False):
    return file_func(shutil.copy, src, dst, overwrite)

def move(src, dst, overwrite = False):
    return file_func(shutil.move, src, dst, overwrite)

def audio_duration(file):
    mutafile = mutagen.File(file, easy=True)
    if mutafile is not None:
        return mutafile.info.length
    else:
        return float("inf")  # unrecognized sound files and non sound files


def copy_and_tag(src, dst, gamename, overwrite = False):
    dst = copy(src, dst, overwrite)
    tag(dst, gamename)

def move_and_tag(src, dst, gamename, overwrite = False):
    dst = move(src, dst, overwrite)
    tag(dst, gamename)

def remove_empty_dir_tree(path):
    path = Path(path)
    for child in path.glob("*"):
        if child.is_dir():
            remove_empty_dir_tree(child)
            try:
                child.rmdir()
            except:
                pass
    try:
        path.rmdir()
    except:
        pass