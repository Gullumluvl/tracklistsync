#!/usr/bin/env python3

"""Randomly select tracks from a m3u playlist, limited to a given storage capacity"""

from __future__ import print_function

from sys import stdin, stdout, stderr
import argparse
from playlisttools import iter_playlist, fixedsize_sample, write_paths, humanize_number


def main(infile, outfile, maxsize='8GiB', epsilon='3MiB'):
    urlset = set(iter_playlist(infile))
    size, sample = fixedsize_sample(urlset, maxsize, epsilon)
    print("# Playlist size " + humanize_number(size))
    write_paths(sample, outfile)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('infile', nargs='?', type=argparse.FileType('r'),
                        default=stdin)
    parser.add_argument('outfile', nargs='?', type=argparse.FileType('w'),
                        default=stdout)
    parser.add_argument('-s', '--maxsize', default='8GiB',
                        help='maximum cumulated file size of the playlist [%(default)s]')
    parser.add_argument('-e', '--epsilon', default='300KiB',
                        help='convergence threshold [%(default)s]')
    args = parser.parse_args()
    main(**vars(args))
