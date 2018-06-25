#!/usr/bin/env python3

"""
Print the total size of files contained in the playlist.
"""

from sys import stdin
import argparse
from playlisttools import get_playlist_filesize, humanize_number


def main(playlistfile):
    ntot, nf, bytesize = get_playlist_filesize(playlistfile)
    readablesize = humanize_number(bytesize)
    print("%d/%d files: %s (%s)" %(ntot - nf, ntot, bytesize, readablesize))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('playlistfile', nargs='?', type=argparse.FileType('r'),
                        default=stdin)
    args = parser.parse_args()
    main(args.playlistfile)
