"""Synchronize local folders with Imgur albums.
"""

import argparse
import pathlib

from . import client
from . import actions


base_dir = pathlib.Path(__file__).parent.parent


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-c", "--credentials", type=pathlib.Path, default=base_dir / "credentials.json")
    parser.add_argument("-t", "--token", type=pathlib.Path, default=pathlib.Path.home() / ".config" / "imgit" / "token.json")
    actions_parser = parser.add_subparsers(dest="action", help="Action to perform")
    clone = actions_parser.add_parser("clone", help="Clone an album to a local folder")
    clone.add_argument("url", help="URL of the album to clone")
    clone.add_argument("folder", type=str, help="Local folder to clone the album to", nargs="?")
    status = actions_parser.add_parser("status", help="Print album details")
    args = parser.parse_args()
    client_ = client.Client(args.credentials)
    try:
        if args.action == "clone":
            actions.clone(client_, args.url, args.folder)
        elif args.action == "status":
            actions.status()
    except client.QuotaError as err:
        print(bcolors.WARNING + "Imgur Error: " + str(err) + bcolors.ENDC)
    except client.ImgurError as err:
        print(bcolors.FAIL + "Imgur Error: " + str(err) + bcolors.ENDC)
    except actions.ImgitError as err:
        print(bcolors.FAIL + "Error: " + str(err) + bcolors.ENDC)