""" Based on UnityPy.tools.extractor """

from collections.abc import Callable
from io import BytesIO
import os
from pathlib import Path
from typing import Union, List
import UnityPy
from UnityPy.classes import (
    Object,
    PPtr,
)
from UnityPy.enums.ClassIDType import ClassIDType
from UnityPy.tools.extractor import EXPORT_TYPES, exportMonoBehaviour

def export_obj(
    obj: Union[Object, PPtr],
    fp: Path,
    append_name: bool = False,
    append_path_id: bool = False,
    export_unknown_as_typetree: bool = False,
    asset_filter: Callable[[Object], bool] = None,
) -> List[int]:
    """Exports the given object to the given filepath.

    Args:
        obj (Object, PPtr): A valid Unity object or a reference to one.
        fp (Path): A valid filepath where the object should be exported to.
        append_name (bool, optional): Decides if the obj name will be appended to the filepath. Defaults to False.
        append_path_id (bool, optional): Decides if the obj path id will be appended to the filepath. Defaults to False.
        export_unknown_as_typetree (bool, optional): If set, then unimplemented objects will be exported via their typetree or dumped as bin. Defaults to False.
        asset_filter (func(Object)->bool, optional): Determines whether to export an object. Defaults to all objects.

    Returns:
        list: a list of exported object path_ids
    """
    # figure out export function
    type_name = obj.type.name
    export_func = EXPORT_TYPES[getattr(ClassIDType,type_name)]
    if not export_func:
        if export_unknown_as_typetree:
            export_func = exportMonoBehaviour
        else:
            return []

    # set filepath
    obj = obj.read()

    if asset_filter and not asset_filter(obj):
        return []

    if append_name:
        fp = os.path.join(fp, obj.name if obj.name else type_name)

    fp, extension = os.path.splitext(fp)

    if append_path_id:
        fp = f"{fp}_{obj.path_id}"

    # TODO convert wav samples to target format ogg/flac/mp3/etc
    return export_func(obj, fp, extension)


def extract_assets(
    src: Union[Path, BytesIO, bytes, bytearray],
    dst: Path,
    use_container: bool = True,
    ignore_first_container_dirs: int = 0,
    append_path_id: bool = False,
    export_unknown_as_typetree: bool = False,
    asset_filter: Callable[[Object], bool] = None,
) -> List[int]:
    """Extracts some or all assets from the given source.

    Args:
        src (Union[Path, BytesIO, bytes, bytearray]): [description]
        dst (Path): [description]
        use_container (bool, optional): [description]. Defaults to True.
        ignore_first_container_dirs (int, optional): [description]. Defaults to 0.
        append_path_id (bool, optional): [description]. Defaults to False.
        export_unknown_as_typetree (bool, optional): [description]. Defaults to False.
        asset_filter (func(object)->bool, optional): Determines whether to export an object. Defaults to all objects.

    Returns:
        List[int]: [description]
    """
    # load source
    env = UnityPy.load(src)
    exported = []

    export_types_keys = list(EXPORT_TYPES.keys())

    def defaulted_export_index(type: ClassIDType):
        try:
            return export_types_keys.index(type)
        except (IndexError, ValueError):
            return 999

    if use_container:
        container = sorted(env.container, key=lambda x: defaulted_export_index(x[1].type))
        for obj_path, obj in container:
            if (not asset_filter) or asset_filter(obj):
                # the check of the various sub directories is required to avoid // in the path
                obj_dest = os.path.join(
                    dst,
                    *(x for x in obj_path.split("/")[:ignore_first_container_dirs] if x),
                )
                os.makedirs(os.path.dirname(obj_dest), exist_ok=True)
                exported.extend(
                    export_obj(
                        obj,
                        obj_dest,
                        append_path_id=append_path_id,
                        export_unknown_as_typetree=export_unknown_as_typetree,
                        asset_filter=asset_filter,
                    )
                )

    else:
        objects = sorted(env.objects, key=lambda x: defaulted_export_index(x.type))
        for obj in objects:
            # print(obj.type)
            if (not asset_filter) or asset_filter(obj):
                # for k in dir(obj):
                #     print(" ", k, getattr(obj,k))
                if obj.path_id not in exported:
                    exported.extend(
                        export_obj(
                            obj,
                            dst,
                            append_name=True,
                            append_path_id=append_path_id,
                            export_unknown_as_typetree=export_unknown_as_typetree,
                            asset_filter=asset_filter,
                        )
                    )

    return exported