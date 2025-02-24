import dataclasses
import json
import pathlib


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