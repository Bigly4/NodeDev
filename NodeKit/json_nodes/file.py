import bpy
import os
import shutil
from typing import Any, get_type_hints
import json
import logging
import re
import copy
from bpy.path import abspath
from .. import config

log = logging.getLogger(__name__)


def make_valid_filename(name: str, uuid_str: str, ext: str) -> str:

    safe = re.sub(
        config.INVALID_FILENAME_CHARS, config.FILENAME_REPLACEMENT_CHAR, name
    ).strip()
    return f"{safe}_{uuid_str}{ext}"


def setup(folder_path: str) -> None:
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    os.makedirs(folder_path, exist_ok=True)


def write_trees_to(folder_path: str, tree_dicts: list[dict]) -> None:
    for tree_dict in tree_dicts:

        directory = os.path.join(
            folder_path, tree_dict["tree_type"], tree_dict["category"]
        )
        os.makedirs(directory, exist_ok=True)
        filename = make_valid_filename(
            tree_dict["name"], tree_dict["tree"]["uuid"], ".json"
        )
        filepath = os.path.join(directory, filename)
        json.dump(
            tree_dict,
            open(filepath, "w"),
            indent=4,
        )


def read_trees_from(folder_path: str) -> list[dict[str, Any]]:
    data_dicts = []
    for file in os.listdir(folder_path):
        if file.endswith(".json"):
            with open(f"{folder_path}/{file}", "r") as f:
                data_dict = json.load(f)
                data_dicts.append(data_dict)
        if os.path.isdir(f"{folder_path}/{file}"):
            subfolder_data = read_trees_from(f"{folder_path}/{file}")
            data_dicts.extend(subfolder_data)
    return data_dicts


def validate_path(folder_path: str) -> str:
    folder_path = abspath(folder_path)
    try:
        if not folder_path:
            return "Select a directory to store the JSON files"
        elif not os.path.exists(folder_path):
            return "Path does not exist"
        elif not os.path.isdir(folder_path):
            return "Path is not a directory"
        else:
            return _check_folder_structure(folder_path)
    except Exception as e:
        log.error(f"Error validating path {folder_path}: {e}")
        return "An internal error occurred while validating the path"


def _check_folder_structure(folder_path: str) -> str:
    for tree_type in os.listdir(folder_path):
        if tree_type == config.ASSETS_FOLDER:
            for asset_type in os.listdir(os.path.join(folder_path, tree_type)):
                if asset_type not in config.ASSET_TYPES:
                    return f"Unexpected asset type folder '{asset_type}' found in '{tree_type}'"
                for asset_file in os.listdir(
                    os.path.join(folder_path, tree_type, asset_type)
                ):
                    if not asset_file.endswith(".blend"):
                        return f"Unexpected file '{asset_file}' found in '{tree_type}:{asset_type}'"
        elif tree_type not in config.SUPPORTED_TREE_TYPES:
            return f"Unexpected folder '{tree_type}' found"
        else:
            for category in os.listdir(os.path.join(folder_path, tree_type)):
                if category not in [config.CATEGORY_TESTS, config.CATEGORY_GROUPS]:
                    return f"Unexpected category '{category}' found in '{tree_type}'"

                for file in os.listdir(os.path.join(folder_path, tree_type, category)):
                    if not (file.endswith(".json") or file.endswith(".blend")):
                        return f"Unexpected file '{file}' found in '{tree_type}:{category}'"
                    elif _check_json(
                        os.path.join(folder_path, tree_type, category, file)
                    ):
                        return f"Invalid JSON structure in file '{file}' in '{tree_type}:{category}'"
    return ""


def number_of_files(folder_path: str, ext: str) -> int:
    counter = 0
    if not bpy.context.scene.node_kit.directory_error:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith(ext):
                    counter += 1
    return counter


def folder_is_empty(folder_path: str) -> bool:
    return len(os.listdir(folder_path)) == 0


def _check_json(file_path: str) -> str:
    try:
        with open(file_path, "r") as file:
            json_dict = json.load(file)
        if not _is_typed_dict(json_dict, config.ExportDict):
            return f"Invalid JSON structure in file {file_path}"
    except json.JSONDecodeError as e:
        return f"Invalid JSON in file {file_path}: {e}"
    return ""


def _is_typed_dict(data: dict, typed_dict_class) -> bool:
    """Validate if a dictionary matches a TypedDict structure"""
    keys = data.keys()
    types = get_type_hints(typed_dict_class)

    if keys != types.keys():
        log.debug(f"Keys mismatch: {keys} != {types.keys()}")
        return False
    for key in keys:
        if not isinstance(data[key], types[key]):
            log.debug(f"Key {key} has wrong type")
            return False
    return True
