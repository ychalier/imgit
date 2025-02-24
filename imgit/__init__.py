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
    clone = actions_parser.add_parser("clone", help="Clone an album to a local folder")
    clone.add_argument("url", help="URL of the album to clone")
    clone.add_argument("folder", type=str, help="Local folder to clone the album to", nargs="?")
    actions_parser.add_parser("status", help="Print album details")
    actions_parser.add_parser("fetch", help="Fetch album index")
    actions_parser.add_parser("diff", help="Compare local and remote indexes")
    actions_parser.add_parser("pull", help="Download images")
    actions_parser.add_parser("push", help="Upload images")
    actions_parser.add_parser("sync", help="Pull and push")
    args = parser.parse_args()
    client_ = client.Client(args.credentials)
    try:
        if args.action == "clone":
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
    except models.QuotaError as err:
        utils.printc("Imgur Error: " + str(err), "yellow")
    except models.ImgurError as err:
        utils.printc("Imgur Error: " + str(err), "red")
    except models.ImgitError as err:
        utils.printc("Error: " + str(err), "red")