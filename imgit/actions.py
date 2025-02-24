import os
import pathlib
import re
import tqdm

from .client import Client
from . import models
from . import utils


IMGIT_FOLDER = ".imgit"
ACCEPTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".mp4"]


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
    diff(path)
    # TODO: pull


def load_album(root: pathlib.Path) -> models.Album:
    path = root / IMGIT_FOLDER / "meta.json"
    if not path.exists():
        raise models.ImgitError("Error: Not an imgit folder")
    return utils.read_dataclass(models.Album, path)


def load_index(root: pathlib.Path) -> models.Index:
    path = root / IMGIT_FOLDER / "index.json"
    if not path.parent.exists():
        raise models.ImgitError("Error: Not an imgit folder")
    if not path.exists():
        return models.Index()
    images = utils.read_dataclass_list(models.Image, path)
    return models.Index.from_list(images)


def write_index(root: pathlib.Path, index: models.Index):
    path = root / IMGIT_FOLDER / "index.json"
    if not path.parent.exists():
        raise models.ImgitError("Error: Not an imgit folder")
    utils.write_dataclass_list(list(index.values()), path)


def status(root: pathlib.Path = pathlib.Path(".")):
    album = load_album(root)
    index = load_index(root)
    download, upload, change = diff(root)
    print(f"{album.title} [{album.link}] #{len(index)}")
    if not (download or upload or change):
        print("Up to date.")
    for image in download:
        utils.printc("↓ " + image.path, "cyan")
    for image in upload:
        utils.printc("↑ " + image.path, "green")
    for image in change:
        utils.printc("~ " + image.path, "blue")
    

def fetch(client: Client, root: pathlib.Path = pathlib.Path(".")):
    album = load_album(root)
    index = load_index(root)
    remote_index = client.get_album_images(album.id)
    for image in remote_index.values():
        if image.path in index:
            index[image.path].remote_id = image.remote_id
            index[image.path].remote_datetime = image.remote_datetime
            index[image.path].remote_size = image.remote_size
            index[image.path].remote_delete_hash = image.remote_delete_hash
            index[image.path].remote_link = image.remote_link
        else:
            index.add(image)
    for image in list(index.values()):
        if image.path not in remote_index:
            if not image.offline:
                del index[image.path]
            else:
                index[image.path].remote_id = None
                index[image.path].remote_datetime = None
                index[image.path].remote_size = None
                index[image.path].remote_delete_hash = None
                index[image.path].remote_link = None
    write_index(root, index)


def build_local_index(root: pathlib.Path) -> models.Index:
    imgit_path = root / IMGIT_FOLDER
    if not imgit_path.exists():
        raise models.ImgitError("Error: Not an imgit folder")
    index = models.Index()
    for top, _, filenames in os.walk(root):
        folder = root / top
        if folder.as_posix().startswith(imgit_path.as_posix()):
            continue
        for filename in filenames:
            path = folder / filename
            md5 = utils.hash_file(path)
            stat = path.stat()
            index.add(models.Image(
                path=path.relative_to(root).as_posix(),
                local_size=stat.st_size,
                local_ctime=stat.st_ctime,
                local_mtime=stat.st_mtime,
                local_md5=md5,
                remote_id=None,
                remote_datetime=None,
                remote_size=None,
                remote_delete_hash=None,
                remote_link=None,
            ))
    return index


def diff(root: pathlib.Path = pathlib.Path(".")
         ) -> tuple[list[models.Image], list[models.Image], list[models.Image]]:
    album = load_album(root)
    index = load_index(root)
    local_index = build_local_index(root)
    download = []
    for image in index.values():
        if image.online and image.path not in local_index:
            download.append(image)
    upload = []
    for image in local_index.values():
        if image.path not in index or not index[image.path].online:
            upload.append(image)
    change = []
    for image in local_index.values():
        if image.path in index and index[image.path].online and index[image.path].offline and index[image.path].local_md5 != image.local_md5:
            change.append(image)
    return download, upload, change


def pull(client: Client, root: pathlib.Path = pathlib.Path(".")):
    album = load_album(root)
    index = load_index(root)
    download, upload, change = diff(root)
    pbar = tqdm.tqdm(total=len(download), unit="image")
    for image in download:
        path = root / image.path
        pbar.set_description(path.name)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            client.download(image.remote_link, path)
        except models.ImgurError as err:
            pbar.close()
            write_index(root, index)
            raise err
        md5 = utils.hash_file(path)
        stat = path.stat()
        index[image.path].local_size = stat.st_size
        index[image.path].local_ctime = stat.st_ctime
        index[image.path].local_mtime = stat.st_mtime
        index[image.path].local_md5 = md5
        pbar.update(1)
    pbar.close()
    write_index(root, index)