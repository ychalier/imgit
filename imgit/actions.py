import pathlib
import re

from .client import Client, Album, Image
from . import utils


IMGIT_FOLDER = ".imgit"


class ImgitError(Exception):
    pass


def extract_album_id(url: str) -> str | None:
    m = re.match(r"^([a-zA-Z0-9]{7})$", url.strip())
    if m is not None: return m.group(1)
    m = re.match(r"^https://imgur.com/a/([a-zA-Z0-9]{7})$", url.strip())
    if m is not None: return m.group(1)
    m = re.match(r"^https://imgur.com/a/.+\-([a-zA-Z0-9]{7})$", url.strip())
    if m is not None: return m.group(1)
    return None


def clone(client: Client, url: str, folder: str | None = None):
    """Clone an album to a local folder.
    """
    album_id = extract_album_id(url)
    if album_id is None:
        raise ValueError(f"Could not extract album id from {url}")
    album = client.get_album(album_id)
    if folder is None:
        folder = album.title
    path = pathlib.Path(folder)
    print(f"Cloning into '{path.as_posix()}'...")
    if path.exists():
        if not utils.confirm(f"Folder {folder} already exists. Do you wish to continue?"):
            return
    (path / IMGIT_FOLDER).mkdir(parents=True, exist_ok=True)
    utils.write_dataclass(album, path / IMGIT_FOLDER / "meta.json")
    fetch(client, path)
    # TODO: diff
    # TODO: pull


def load_album(root: pathlib.Path) -> Album:
    path = root / IMGIT_FOLDER / "meta.json"
    if not path.exists():
        raise ImgitError("Not an imgit folder")
    return utils.read_dataclass(Album, path)


def load_remote(root: pathlib.Path) -> list[Image]:
    path = root / IMGIT_FOLDER / "remote.json"
    if not path.exists():
        raise ImgitError("Not an imgit folder")
    return utils.read_dataclass_list(Image, path)


def status(root: pathlib.Path = pathlib.Path(".")):
    album = load_album(root)
    images = load_remote(root)
    print(f"{album.title} [{album.id}] {album.link}")
    print(f"{len(images)} images")
    # TODO: show diff with local


def fetch(client: Client, root: pathlib.Path = pathlib.Path(".")):
    album = load_album(root)
    images = client.get_album_images(album.id)
    utils.write_dataclass_list(images, root / IMGIT_FOLDER / "remote.json")