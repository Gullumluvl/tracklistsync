#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import sys
import argparse as ap
import datetime as dt


def parse_songlengths(stream=sys.stdin):
    return [line.rstrip().split('\t') for line in stream]


def lengths2times(songlengths, tfmt='%M:%S'):
    time0 = dt.datetime(1, 1, 1)
    songtimes = []
    prev_td = dt.timedelta()
    for song, length in songlengths:
        start_time = (time0 + prev_td)
        out_fmt = '%H:%M:%S' if prev_td.total_seconds() > 3600 else '%M:%S'
        songtimes.append(start_time.strftime(out_fmt))

        t = dt.datetime.strptime(length, tfmt)
        td = dt.timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
        prev_td += td
    total_time = time0 + prev_td
    out_fmt = '%H:%M:%S' if prev_td.total_seconds() > 3600 else '%M:%S'
    return songtimes, total_time.strftime(out_fmt)


def main():
    parser = ap.ArgumentParser(description=__doc__)
    parser.add_argument('songlengths', nargs='?', type=ap.FileType('r'), default=sys.stdin)
    args = parser.parse_args()
    
    songlengths = parse_songlengths(args.songlengths)
    songtimes, total_length = lengths2times(songlengths)

    for (song, _), t in zip(songlengths, songtimes):
        print('%s    %s' % (t, song))
    print('Total:   %s' % total_length)


if __name__ == '__main__':
    main()
