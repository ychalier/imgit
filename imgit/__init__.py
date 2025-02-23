"""Synchronize local folders with Imgur albums.
"""

import argparse


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    actions_parser = parser.add_subparsers(dest="action", help="Action to perform")
    clone_parser = actions_parser.add_parser("clone", help="Clone an album to a local folder")
    clone_parser.add_argument("url", help="URL of the album to clone")
    clone_parser.add_argument("folder", type=str, help="Local folder to clone the album to", nargs="?")
    args = parser.parse_args()
    if args.action == "clone":
        from .actions import clone
        clone(args.url, args.folder)