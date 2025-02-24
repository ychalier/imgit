import dataclasses
import hashlib
import json
import pathlib


class bcolors:
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DARKCYAN = '\033[36m'


def printc(message: str, color: str):
    marker = {
        "green": bcolors.GREEN,
        "blue": bcolors.BLUE,
        "cyan": bcolors.CYAN,
        "red": bcolors.RED,
        "yellow": bcolors.YELLOW,
        "purple": bcolors.PURPLE,
        "bold": bcolors.BOLD,
        "underline": bcolors.UNDERLINE,
        "darkcyan": bcolors.DARKCYAN
    }[color]
    print(marker + message + bcolors.ENDC)


def format_duration(seconds: int | float) -> str:
    hours = int(seconds / 3600)
    minutes = int((seconds - 3600 * hours) / 60)
    seconds = int(seconds - 3600 * hours - 60 * minutes)
    if hours > 0:
        return f"{hours}h{minutes:02d}"
    return f"{minutes}:{seconds:02d}"


def confirm(prompt: str) -> bool:
    answer = input(prompt + " (y/n)\n>>> ")
    if answer.strip().lower() in ["y", "o", "yes", "oui"]:
        return True
    return False


def read_dataclass(cls, path: str | pathlib.Path):
    with open(path, "r", encoding="utf8") as file:
        data = json.load(file)
    return cls(**data)


def write_dataclass(obj, path: str | pathlib.Path):
    with open(path, "w", encoding="utf8") as file:
        json.dump(dataclasses.asdict(obj), file, indent=4, default=str)


def read_dataclass_list(cls, path: str | pathlib.Path):
    with open(path, "r", encoding="utf8") as file:
        data = json.load(file)
    return [cls(**row) for row in data]


def write_dataclass_list(obj, path: str | pathlib.Path):
    with open(path, "w", encoding="utf8") as file:
        json.dump([dataclasses.asdict(o) for o in obj], file, indent=4, default=str)


def hash_file(path: str | pathlib.Path, size: int = 1024) -> str:
    md5 = hashlib.md5()
    with open(path, "rb") as file:
        data = file.read(size)
        md5.update(data)
    return md5.hexdigest()
