#!/usr/bin/env python

"""
DESCRIPTION
    Use a .m3u file to synchronize the audio files to an other
    directory/device.  Check first which tracks are present in the new
    directory, propose to replace if file differs (quality for example).
    Synchronize files according to metadata, for example
    `artist/album/tracknb-title.ext`
"""

import os
import errno   # symbolic codes for error types
import os.path
import sys
import re
import shutil
import urllib
import argparse
import mutagen
#import 

# Steps
# Load file list from .m3u
#   Show files not found.
#   
# Build list of audio tracks already there.
#   Try to guess tags from file name if no tags
#   Identify conflicting files
#   Ask what to do with conflicting files
#
# Check that there is enough space
# If not, ask to start copying a anyway
# Copy files to be copied according to the pattern


exts = ['mp3', 'ogg', 'flac', 'wma', 'm4a', 'wav']

short2long = {'a': 'artist',
              'b': 'album' ,
              'n': 'number',
              't': 'title' ,
              'y': 'year'  }
id3tags = {'artist': 'tpe1',
           'a'     : 'tpe1',
           'album' : 'talb',
           'b'     : 'talb',
           'number': 'trck',
           'n'     : 'trck',
           'title' : 'tit2',
           't'     : 'tit2',
           'year'  : 'tdrc',
           'y'     : 'tdrc'}
id3tags_set = set(id3tags.values())
id3v2tags = {'artist': 'TPE1',
             'a'     : 'TPE1',
             'album' : 'TALB',
             'b'     : 'TALB',
             'number': 'TRCK',
             'n'     : 'TRCK',
             'title' : 'TIT2',
             't'     : 'TIT2',
             'year'  : 'TYER',
             'y'     : 'TYER'}
id3v2tags_set = set(id3v2tags.values())
m4atags = {'artist': '\xa9ART', # or 'aART', '\xa9wrt' ?
           'a'     : '\xa9ART',
           'album' : '\xa9alb',
           'b'     : '\xa9alb',
           'number': 'trkn',
           'n'     : 'trkn',
           'title' : '\xa9nam',
           't'     : '\xa9nam',
           'year'  : '\xa9day',
           'y'     : '\xa9day'}
m4atags_set = set(m4atags.values())
wmatags = {'artist': 'Author',
           'a'     : 'Author',
           'album' : 'WM/AlbumTitle',
           'b'     : 'WM/AlbumTitle',
           'number': 'WM/TrackNumber',
           'n'     : 'WM/TrackNumber',
           'title' : 'Title',
           't'     : 'Title',
           'year'  : 'WM/Year',
           'y'     : 'WM/Year'}
wmatags_set = set(wmatags.values())


def readm3u(playlistfile):
    """Return the set of files of the playlist, and its size in bytes"""
    fileset = set()
    s = 0  # total size of files
    nf = 0 # number of files not found
    with open(playlistfile) as F:
        for line in F.readlines():
            if not line.startswith('#'):
                path = urllib.unquote(line.rstrip().replace('file://', ''))
                fileset.add(path)
                try:
                    s += os.path.getsize(path)
                except OSError:
                    print >>sys.stderr, "Not found: %r" % path
                    nf += 1
    ntot = len(fileset)
    bytesize = make_human_bytesize(s)
    readablesize = make_readable_number(s)

    print "%d/%d files: %s (%s)" %(ntot - nf, ntot, bytesize, readablesize)
    return fileset, s


def make_readable_number(s):
    """return string representation of big number, with commas between
    thousands"""
    strsize = str(s)
    readablesize=''
    while strsize:
        readablesize = strsize[-3:] + ',' + readablesize
        strsize = strsize[:-3]
    readablesize = readablesize[:-1]
    return readablesize


def make_human_bytesize(s, precision=1):
    power = 0
    units = ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']
    while s / 1024**(power+1):
        power += 1
    bytesize = "%4.*f %sB" % (precision, float(s) / 1024**power, units[power])
    return bytesize


def make_minutes(t):
    m = int(t) / 60
    s = int(t) % 60
    return "%s min %s s" % (m,  s)


def pattern2python(pattern):
    """Convert format string of type '%a' to python type '{a}'
    Keys:
        %% : percentage sign
        %a : artist
        %b : album
        %n : track number
        %t : title
        %y : year
    """
    reg = re.compile(r'%([abnty%])')
    ppattern = reg.sub(r'{\1}', pattern)
    return ppattern.replace('{n}', '{n:0>2s}')


def file_audioscan(f, metadata, rmetadata):
    audiofile = mutagen.File(f)
    metadata[f] = {}
    metadata[f]['bitrate'] = audiofile.info.bitrate
    metadata[f]['length'] = audiofile.info.length
    try:
        tagkeys = set(audiofile.tags.keys())
    except AttributeError:
        # File not tagged.
        return
    # gather audio tags
    if f.endswith('.mp3') or f.endswith('.MP3'):
        tags = id3tags
        if tagkeys & id3v2tags_set:
            tags = id3v2tags
            #raise NotImplementedError("unrecognized tags: %s" % f)
        for k in 'abnty': #y caused trouble
            try:
                metadata[f][k] = audiofile[tags[k]].text[0]
            except KeyError, e:
                pass # handled later using .get()
    elif f.endswith('.m4a'):
        tags = m4atags
        for k in 'abnty': #y caused trouble
            try:
                metadata[f][k] = audiofile[tags[k]][0]
            except KeyError:
                pass
                #print >>sys.stderr, "tag not found %s: %s" % \
                #                        (k, tags[k])
    elif f.endswith('.wma'):
        tags = wmatags
        for k in 'at':
            try:
                metadata[f][k] = audiofile[tags[k]][0]
            except KeyError:
                pass
        for k in 'bny':
            try:
                metadata[f][k] = audiofile[tags[k]][0].value
            except KeyError:
                pass
    else:
        raise NotImplementedError("unimplemented tag formats: %s" % f )
    # associate tags to filename for reverse search
    try:
        artist = rmetadata.setdefault(metadata[f].get('a', 'unknown artist'), {})
        album = artist.setdefault(metadata[f].get('b', 'unknown album'), {})
        title = album.setdefault(metadata[f].get('t', 'unknown track'), set())
        title.add(f)
    except (KeyError, TypeError):
        print >>sys.stderr, f, metadata[f]
        raise


def dir_audioscan(destdir):
    """Build list of tracks and associated metadata in a directory.
    WARNING: Have no idea how many files it can handle without crashing"""
    # Warning: files with same name but different tags?
    metadata = {}
    rmetadata = {}
    reg = re.compile(r'\.(' + r'|'.join(exts) + ')$')
    for root, _, files in os.walk(destdir):
        for f in files:
            if reg.search(f):
                file_audioscan(os.path.join(root, f), metadata, rmetadata)
    return metadata, rmetadata


def sync(playlistfile, destdir, pattern="%a/%b/%n-%t", localdirs=["~/Musique/"],
         ignore_all=False):
    localregs = [re.compile(r'^' + os.path.expanduser(L)) for L in localdirs]
    ppattern = pattern2python(pattern)
    statvfs = os.statvfs(destdir)
    avail = statvfs.f_bfree * statvfs.f_frsize  # available space
    total = statvfs.f_blocks * statvfs.f_frsize # total size of filesystem
    print >>sys.stderr, "Scanning destination..."
    dmetadata, drmetadata = dir_audioscan(destdir)
    print >>sys.stderr, "Reading playlist"
    fileset, s = readm3u(playlistfile)
    # TODO: update s depending on already existing files in destination
    if s >= avail:
        hs = make_human_bytesize(s)
        ha = make_human_bytesize(avail)
        print >>sys.stderr, "Warning: %s to transfer VS free space: %s" % (hs, ha)
        answer = ''
        while answer not in ['a', 'c']:
            answer = raw_input("What to do? Abort (a) or copy until full (c): ")
        if answer == 'a':
            return 1

    print >>sys.stderr, "Copying files..."
    lmetadata, lrmetadata = {}, {}
    for f in sorted(list(fileset)):
        file_audioscan(f, lmetadata, lrmetadata)
        a = lmetadata[f].get('a')
        b = lmetadata[f].get('b')
        t = lmetadata[f].get('t')
        n = lmetadata[f].get('n')
        _, ext = os.path.splitext(f)
        if all((a, b, t, n)):
            lmetadata[f]['a'] = a.replace('/', '-').rstrip()
            lmetadata[f]['b'] = b.replace('/', '-').rstrip()
            lmetadata[f]['t'] = t.replace('/', '-').rstrip()
            lmetadata[f]['n'] = str(n).replace('/', '-').rstrip()
            try:
                destf = os.path.join(destdir, ppattern.format(**lmetadata[f])) + ext
            except UnicodeEncodeError:
                for k in 'abtn':
                    lmetadata[f][k] = lmetadata[f][k].encode('utf8')
                destf = os.path.join(destdir, ppattern.format(**lmetadata[f])) + ext
        else:
            i = 0
            while i <= len(localregs) and not localregs[i].match(f):
                i += 1
            try:
                destsubdirs = localregs[i].sub('', f)
            except IndexError:
                print >>sys.stderr, "No matching localdir for %s, %s" % \
                        (f, localdirs)
            destf = os.path.join(destdir, destsubdirs) + ext
        dfset = drmetadata.get(a, {}).get(b, {}).get(t)
        if dfset:
            if not ignore_all:
                for df in dfset:
                    print >>sys.stderr, "Warning: Song {a} - {t} ({b})".\
                                                        format(**lmetadata[f])
                    print >>sys.stderr, "already exists in destination."
                    dbr = str(dmetadata[df]['bitrate'] / 1000) + ' kbps'
                    dle = make_minutes(dmetadata[df]['length'])
                    lbr = str(lmetadata[f]['bitrate'] / 1000) + ' kbps'
                    lle = make_minutes(lmetadata[f]['length'])
                    print >>sys.stderr, "Replace %s (%s, %s)" % (df, dbr, dle)
                    print >>sys.stderr, "by %s (%s, %s) ?" % (f, lbr, lle)
                    answer = ''
                    if os.path.split(df)[1] == os.path.split(destf)[1]:
                        while answer not in ['r', 'i']:
                            answer = raw_input("Replace (r) / Ignore (i) : ")
                        if answer == 'r': answer = 'c' # consistent behavior
                    else:
                        while answer not in ['r', 'c', 'i']:
                            answer = raw_input("Replace (r) / Ignore (i) / Copy alongside (c): ")
                    if answer != 'i':
                        if answer == 'r':
                            os.remove(df)
                        try:
                            os.makedirs(os.path.split(destf)[0])
                        except OSError as e:
                            #if e.errno != errno.EEXIST:
                                #print >>sys.stderr, e # Beware errno.EINVAL
                                # TODO: try to use original path
                                #raise
                            if e.errno == errno.EINVAL:
                                print >>sys.stderr, "Adapting file name: %s" % destf
                                destf = destf.replace(':', '-').replace('?', '-')
                                # recursively call the function
                                try:
                                    os.makedirs(os.path.split(destf)[0])
                                except OSError as e:
                                    if e.errno != errno.EEXIST:
                                        print >>sys.stderr, e # Beware errno.EINVAL
                        try:
                            shutil.copy2(f, destf)
                        except IOError as e:
                            if e.errno == errno.ENOSPC:
                                # "No space left on device"
                                print >>sys.stderr, "Could not copy %s (%s)" % \
                                        (f, e.strerror)
                                os.remove(destf)
                                return
                            else:
                                raise

        else:
            # TODO: Make a function for this
            try:
                os.makedirs(os.path.split(destf)[0])
            except OSError as e:
                #if e.errno != errno.EEXIST:
                    #print >>sys.stderr, e # Beware errno.EINVAL
                    # TODO: try to use original path
                    #raise
                if e.errno == errno.EINVAL:
                    print >>sys.stderr, "Adapting file name: %s" % destf
                    destf = destf.replace(':', '-').replace('?', '-')
                    # recursively call the function
                    try:
                        os.makedirs(os.path.split(destf)[0])
                    except OSError as e:
                        if e.errno != errno.EEXIST:
                            print >>sys.stderr, e # Beware errno.EINVAL
            try:
                # Can choose copyfile, copy or copy2 depending on permissions/metadata
                shutil.copy2(f, destf)
            except IOError as e:
                if e.errno == errno.ENOSPC:
                    # "No space left on device"
                    print >>sys.stderr, "Could not copy %s (%s)" % \
                            (f, e.strerror)
                    print >>sys.stderr, destf
                    os.remove(destf)
                    return
                else:
                    raise

# TODO: When errno 22 occurs, check if device has been disconnected.
# TODO: Parallelize

if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("playlistfile", help=".m3u file")
    parser.add_argument("destdir", help="root of the music directory (destination)")
    parser.add_argument("-p", "--pattern", default="%a/%b/%n-%t",
                        help="structure of the destination folders")
    parser.add_argument("-l", "--localdirs", action='append',
                        default=[], #["~/Music/"],
                        help="roots of the local music directory")
    parser.add_argument("-I", "--ignore-all", action='store_true',
                        help="pass already existing files")
    #sync(playlistfile, destdir, pattern="%a/%b/%n-%t", localdirs=["~/Musique/"]):
    args = parser.parse_args()
    sync(**vars(args))
