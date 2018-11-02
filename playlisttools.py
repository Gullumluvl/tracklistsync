#/usr/bin/env python3


from __future__ import print_function

from sys import stderr, stdout
import os.path as op
from copy import copy
import re

from random import sample

try:
    # Python3
    from urllib.parse import quote, unquote
except ImportError:
    # Python2
    from urllib import quote, unquote


BIBYTES = ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']
BIBYTES_PATTERN = r'^(\d+(?:\.\d+)?) ?(%s)B$' % (r'|'.join(BIBYTES))


def humanize_number(s):
    """Convert a large integer into a human readable string (in GB, MB, etc)"""

    strsize = str(s)
    readablesize = ''
    
    while strsize:
        readablesize = strsize[-3:] + ',' + readablesize
        strsize = strsize[:-3]
    readablesize = readablesize[:-1]

    power = 0
    while s // 1024**(power+1):
        power += 1
    bytesize = "%1.3f %sB" % (float(s) / 1024**power, BIBYTES[power])
    return bytesize


def humannumber2int(bytesize):
    """Convert a number such as 8GB or 4MB to an integer (number of bytes)"""
    # Do not allow more than one number in the string
    #assert len(bytesize.split()) == 1
    bytesize = bytesize.lstrip().rstrip()
    bibytes_regex = re.compile(BIBYTES_PATTERN)
    match = bibytes_regex.match(bytesize)
    assert match, "invalid format"
    number, unit = match.groups()
    
    power = BIBYTES.index(unit)

    return round(float(number) * 1024**power)
    

def iter_playlist(playlistfile):
    """iterate over files from an m3u playlist:
        - unquote the url syntax;
        - do not output duplicates."""
    urlset = set()

    for rawline in playlistfile:
        line = rawline.rstrip()
        if not line.startswith('#'):
            if line not in urlset:
                urlset.add(line)
                yield unquote(line.replace('file://', ''))


def get_playlist_filesize(playlistfile):
    """Read a m3u playlist and output:
    - the number of different files referenced
    - number of unfound files
    - cumulated file size."""
    
    ntot = 0
    notfound = 0
    s = 0
    for path in iter_playlist(playlistfile):
        ntot += 1
        try:
            s += op.getsize(path)
        except OSError:
            print("Not found: %r" % path, file=stderr)
            notfound += 1

    return ntot, notfound, s


def fixedsize_sample(urlset, maxsize="8GiB", epsilon="3MiB"):
    """Random sample the urlset but try to get close to the maxsize."""

    if isinstance(maxsize, str):
        maxsize = humannumber2int(maxsize)

    # Tolerated offset from the maxsize
    if isinstance(epsilon, str):
        epsilon = humannumber2int(epsilon)

    N = len(urlset)
    original_size = sum(op.getsize(path) for path in urlset)
    curr_size = 0
    curr_set = set()

    n_iter = 0
    max_iter = 500
    while  n_iter < max_iter and not (maxsize - epsilon <= curr_size < maxsize):
        n_iter += 1

        # Approximate the number of files to remove/add to get closer.
        space = maxsize - curr_size
        delta_n_files = round(N * abs(space) / original_size)
        # TODO: draw delta_n_files using a normal distribution.
        if delta_n_files == 0:
            delta_n_files += 1
        # TODO: when delta_n_files reaches zero, order urlset by size and
        # select the file with size closest to space. then break.
        
        if space <= 0:
            # Files must be removed from the playlist
            try:
                removed_files = sample(curr_set, delta_n_files)
            except ValueError:
                print("space: %s, delta_n_files: %d" % (space, delta_n_files), file=stderr)
            delta_size = - sum(op.getsize(f) for f in removed_files)
            curr_set.difference_update(removed_files)
        else:
            try:
                added_files = sample(urlset - curr_set, delta_n_files)
            except ValueError:
                print("space: %s, delta_n_files: %d" % (space, delta_n_files), file=stderr)
            delta_size = sum(op.getsize(f) for f in added_files)
            curr_set.update(added_files)

        curr_size += delta_size

    if n_iter == max_iter:
        print("fixedsize_sample() failed to converge", file=stderr)
    else:
        print("Converged in %d iterations." % n_iter, file=stderr)

    return curr_size, curr_set


def write_paths(paths, file=stdout, sort=True):
    
    iter_paths = sorted(paths) if sort else paths
    
    for path in iter_paths:
        file.write('file://' + quote(path) + '\n')

