import fnmatch
import glob
import os
import pathlib
import re
import shutil
import webbrowser

import tqdm

from .client import Client
from . import models
from . import utils
from .gui import GuiServer


def extract_album_id(url: str) -> str | None:
    m = re.match(r"^([a-zA-Z0-9]{7})$", url.strip())
    if m is not None: return m.group(1)
    m = re.match(r"^https://imgur.com/a/([a-zA-Z0-9]{7})$", url.strip())
    if m is not None: return m.group(1)
    m = re.match(r"^https://imgur.com/a/.+\-([a-zA-Z0-9]{7})$", url.strip())
    if m is not None: return m.group(1)
    return None


def clone(client: Client, url: str, folder: str | None = None):
    album_id = extract_album_id(url)
    if album_id is None:
        raise models.ImgitError(f"Could not extract album id from {url}")
    album = client.get_album(album_id)
    if folder is None:
        folder = album.title
    path = pathlib.Path(folder)
    print(f"Cloning into '{path.as_posix()}'...")
    if path.exists():
        if not utils.confirm(f"Folder {folder} already exists. Do you wish to continue?"):
            return
    (path / models.IMGIT_FOLDER).mkdir(parents=True, exist_ok=True)
    utils.write_dataclass(album, path / models.IMGIT_FOLDER / "meta.json")
    fetch(client, path)
    pull(client, path)


def load_album(root: pathlib.Path) -> models.Album:
    path = root / models.IMGIT_FOLDER / "meta.json"
    if not path.exists():
        raise models.ImgitError("Not an imgit folder")
    return utils.read_dataclass(models.Album, path)


def load_index(root: pathlib.Path) -> models.Index:
    path = root / models.IMGIT_FOLDER / "index.json"
    if not path.parent.exists():
        raise models.ImgitError("Not an imgit folder")
    if not path.exists():
        return models.Index()
    images = utils.read_dataclass_list(models.Image, path)
    return models.Index.from_list(images)


def write_index(root: pathlib.Path, index: models.Index):
    path = root / models.IMGIT_FOLDER / "index.json"
    if not path.parent.exists():
        raise models.ImgitError("Not an imgit folder")
    utils.write_dataclass_list(list(index.values()), path)


def status(root: pathlib.Path = pathlib.Path(".")):
    album = load_album(root)
    index = load_index(root)
    download, link, upload, change, delete = diff(root)
    print(f"{album.title} [{album.link}] #{len(index)}")
    if not (download or link or upload or change or delete):
        print("Up to date.")
    for image in download:
        utils.printc("↓ " + image.path, "cyan")
    for image in link:
        utils.printc("↔ " + image.path, "darkcyan")
    for image in upload:
        utils.printc("↑ " + image.path, "green")
    for image in change:
        utils.printc("~ " + image.path, "blue")
    for image in delete:
        utils.printc("x " + image.path, "red")


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


def load_ignore_patterns(path: str | pathlib.Path) -> list[str]:
    with open(path, "r", encoding="utf8") as file:
        patterns = [
            line.strip()
            for line in file
            if line.strip() and not line.startswith('#')
        ]
    return patterns


def is_ignored(path: str, ignore_patterns: list[str]) -> bool:
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern):
            return True
    return False


def build_local_index(root: pathlib.Path) -> models.Index:
    imgit_path = root / models.IMGIT_FOLDER
    if not imgit_path.exists():
        raise models.ImgitError("Not an imgit folder")
    index = models.Index()
    ignore_patterns = []
    if (root / models.IGNORE_NAME).exists():
        ignore_patterns = load_ignore_patterns(root / models.IGNORE_NAME)
    for top, _, filenames in os.walk(root):
        folder = pathlib.Path(top)
        if folder.as_posix().startswith(imgit_path.as_posix()):
            continue
        for filename in filenames:
            path = folder / filename
            if path.suffix not in models.ACCEPTED_EXTENSIONS:
                continue
            if is_ignored(path.as_posix(), ignore_patterns):
                print("Ignored path:", path)
                continue
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
         ) -> tuple[list[models.Image], list[models.Image], list[models.Image], list[models.Image], list[models.Image]]:
    album = load_album(root)
    index = load_index(root)
    local_index = build_local_index(root)
    download = []
    for image in index.values():
        if image.online and image.path not in local_index:
            download.append(image)
    link = []
    for image in local_index.values():
        if image.path in index and index[image.path].online and not index[image.path].offline:
            link.append(image)
    upload = []
    for image in local_index.values():
        if image.path not in index or not index[image.path].online:
            upload.append(image)
    change = []
    for image in local_index.values():
        if image.path in index and index[image.path].online and index[image.path].offline and index[image.path].local_md5 != image.local_md5:
            change.append(image)
    delete = []
    for image in index.values():
        if image.path not in local_index and not index[image.path].online:
            delete.append(image)
    return download, link, upload, change, delete


def pull(client: Client, root: pathlib.Path = pathlib.Path(".")):
    album = load_album(root)
    index = load_index(root)
    download, link = diff(root)[:2]
    if not (download or link):
        print("Pull: already up to date.")
        return
    for image in link:
        index[image.path].local_size = image.local_size
        index[image.path].local_ctime = image.local_ctime
        index[image.path].local_mtime = image.local_mtime
        index[image.path].local_md5 = image.local_md5
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


def push(client: Client, root: pathlib.Path = pathlib.Path(".")):
    album = load_album(root)
    index = load_index(root)
    upload, change, delete = diff(root)[2:]
    if not (upload or change or delete):
        print("Push: already up to date.")
        return
    for image in delete:
        del index[image.path]
    pbar = tqdm.tqdm(total=len(upload) + len(change), unit="image")
    for image in upload:
        path = root / image.path
        pbar.set_description("↑ " + path.name)
        try:
            online_image = client.upload_image(album.id, image, path)
            image.remote_id = online_image.remote_id
            image.remote_datetime = online_image.remote_datetime
            image.remote_link = online_image.remote_link
            image.remote_size = online_image.remote_size
            image.remote_delete_hash = online_image.remote_delete_hash
            index.add(image)
        except Exception as err:
            pbar.close()
            write_index(root, index)
            raise err
        pbar.update(1)
    for image in change:
        path = root / image.path
        pbar.set_description(path.name)
        try:
            client.delete_image(index[image.path].remote_id)
            index[image.path].remote_id = None
            index[image.path].remote_datetime = None
            index[image.path].remote_link = None
            index[image.path].remote_size = None
            index[image.path].remote_delete_hash = None
            online_image = client.upload_image(album.id, image, path)
            image.remote_id = online_image.remote_id
            image.remote_datetime = online_image.remote_datetime
            image.remote_link = online_image.remote_link
            image.remote_size = online_image.remote_size
            image.remote_delete_hash = online_image.remote_delete_hash
            index[image.path] = image
        except Exception as err:
            pbar.close()
            write_index(root, index)
            raise err
        pbar.update(1)
    pbar.close()
    write_index(root, index)


def sync(client: Client, root: pathlib.Path = pathlib.Path(".")):
    pull(client, root)
    push(client, root)


def rm(client: Client, pattern: str, force: bool = False, root: pathlib.Path = pathlib.Path(".")):
    album = load_album(root)
    index = load_index(root)
    delete = set()
    for path in glob.glob(os.path.join(root, pattern)):
        clean_path = (root / path).relative_to(root).as_posix()
        for image in index.values():
            if not image.path.startswith(clean_path):
                continue
            delete.add(image.path)
    if delete:
        if not force:
            for path in delete:
                utils.printc("x " +  path, "red")
            if not utils.confirm("Proceed?"):
                return
        pbar = tqdm.tqdm(total=len(delete), unit="image")
        for image_path in delete:
            path = root / image_path
            pbar.set_description(path.name)
            try:
                client.delete_image(index[image_path].remote_id)
                os.remove(path)
                del index[image_path]
            except Exception as err:
                pbar.close()
                write_index(root, index)
                raise err
            pbar.update(1)
        pbar.close()
        write_index(root, index)
    utils.remove_empty_directories(root)


def mv(client: Client, src: pathlib.Path, dst: pathlib.Path, root: pathlib.Path = pathlib.Path(".")):
    album = load_album(root)
    index = load_index(root)
    src = root / src
    dst = root / dst
    print(src, src.absolute())
    if not src.exists():
        raise models.ImgitError(f"Path does not exist: '{src}'")
    move = []
    if src.is_file():
        move = [(src.relative_to(root).as_posix(), dst)]
    elif src.is_dir():
        for top, dirs, files in os.walk(src):
            for filename in files:
                left = pathlib.Path(top) / filename
                right = dst / pathlib.Path(top).relative_to(src) / filename
                move.append((left.relative_to(root).as_posix(), right))
    for image_path, _ in move:
        if image_path not in index or not index[image_path].online or not index[image_path].offline:
            raise models.ImgitError(f"Trying to move image before it is synced: '{image_path}'")
    pbar = tqdm.tqdm(total=len(move), unit="image")
    for image_path, dst_path in move:
        src_path = root / image_path
        pbar.set_description(src_path.name)
        try:
            new_path = dst_path.relative_to(root).as_posix()
            client.update_image_information(index[image_path].remote_id, new_path)
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(src_path, dst_path)
            image = index[image_path]
            image.path = new_path
            index[new_path] = image
            del index[image_path]
        except Exception as err:
            pbar.close()
            write_index(root, index)
            raise err
        pbar.update(1)
    pbar.close()
    write_index(root, index)
    utils.remove_empty_directories(root)


def init(client: Client, url: str | None = None, root: pathlib.Path = pathlib.Path(".")):
    if (root / models.IMGIT_FOLDER).exists():
        raise models.ImgitError("imgit already initialized")
    if url is None:
        name = root.absolute().name
        album = client.create_album(name)
    else:
        album_id = extract_album_id(url)
        if album_id is None:
            raise models.ImgitError(f"Could not extract album id from {url}")
        album = client.get_album(album_id)
    (root / models.IMGIT_FOLDER).mkdir(parents=True)
    utils.write_dataclass(album, root / models.IMGIT_FOLDER / "meta.json")
    fetch(client, root)


def remove(client: Client, root: pathlib.Path = pathlib.Path(".")):
    album = load_album(root)
    index = load_index(root)
    local_index = build_local_index(root)
    delete = []
    for image in index.values():
        if image.online and not (image.path in local_index):
            delete.append(image)
    for image in delete:
        utils.printc("x " +  image.path, "red")
    if not utils.confirm("Proceed?"):
        return
    pbar = tqdm.tqdm(total=len(delete), unit="image")
    for image in delete:
        path = root / image.path
        pbar.set_description(path.name)
        try:
            client.delete_image(image.remote_id)
            del index[image.path]
        except Exception as err:
            pbar.close()
            write_index(root, index)
            raise err
        pbar.update(1)
    pbar.close()
    write_index(root, index)


def gui(host: str = "127.0.0.1:8000", root: pathlib.Path = pathlib.Path(".")):
    album = load_album(root)
    index = load_index(root)
    server = GuiServer(host, root.absolute(), album, index)
    print(f"Listening to http://{host}, press ^C to stop")
    webbrowser.open(f"http://{host}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
