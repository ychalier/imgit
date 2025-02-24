"""Synchronize local folders with Imgur albums.
"""

import argparse
import pathlib

from . import client
from . import actions
from . import utils
from . import models


base_dir = pathlib.Path(__file__).parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-c", "--credentials", type=pathlib.Path, default=base_dir / "credentials.json")
    parser.add_argument("-t", "--token", type=pathlib.Path, default=pathlib.Path.home() / ".config" / "imgit" / "token.json")
    actions_parser = parser.add_subparsers(dest="action", help="Action to perform")
    init = actions_parser.add_parser("init", help="Initialize a new album with current folder")
    init.add_argument("url", type=str, help="URL of an already existing album", nargs="?")
    clone = actions_parser.add_parser("clone", help="Clone an album to a local folder")
    clone.add_argument("url", type=str, help="URL of the album to clone")
    clone.add_argument("folder", type=str, help="Local folder to clone the album to", nargs="?")
    actions_parser.add_parser("status", help="Print album details")
    actions_parser.add_parser("fetch", help="Fetch album index")
    actions_parser.add_parser("diff", help="Compare local and remote indexes")
    actions_parser.add_parser("pull", help="Download images")
    actions_parser.add_parser("push", help="Upload images and apply changes")
    actions_parser.add_parser("sync", help="Pull and push")
    rm = actions_parser.add_parser("rm", help="Remove a file")
    rm.add_argument("pattern", type=str, help="Image(s) to remove, supports glob pattern")
    rm.add_argument("-f", "--force", action="store_true", help="Do not ask for confirmation")
    mv = actions_parser.add_parser("mv", help="Rename a file or a folder")
    mv.add_argument("src", type=pathlib.Path, help="Source path")
    mv.add_argument("dst", type=pathlib.Path, help="Destination path")
    args = parser.parse_args()
    client_ = client.Client(args.credentials)
    try:
        if args.action == "init":
            actions.init(client_, args.url)
        elif args.action == "clone":
            actions.clone(client_, args.url, args.folder)
        elif args.action == "status":
            actions.status()
        elif args.action == "fetch":
            actions.fetch(client_)
        elif args.action == "diff":
            actions.diff()
        elif args.action == "pull":
            actions.pull(client_)
        elif args.action == "push":
            actions.push(client_)
        elif args.action == "sync":
            actions.sync(client_)
        elif args.action == "rm":
            actions.rm(client_, args.pattern, args.force)
        elif args.action == "mv":
            actions.mv(client_, args.src, args.dst)
    except models.QuotaError as err:
        utils.printc(str(err), "yellow")
    except models.ImgurError as err:
        utils.printc(str(err), "red")
    except models.ImgitError as err:
        utils.printc(str(err), "red")