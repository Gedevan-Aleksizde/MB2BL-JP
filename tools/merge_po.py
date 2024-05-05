#! /usr/bin/env python3
# encoding: utf-8

import argparse
import yaml
from pathlib import Path

import polib
from functions import initializePOFile
from datetime import datetime
from functions import merge_yml

parser = argparse.ArgumentParser()
parser.add_argument('target_dir', type=Path)
parser.add_argument('--output', type=Path, default=Path(f'merged-{datetime.now().strftime("%Y-%m-%dT%H-%M-%S")}.po'))
parser.add_argument('--locale', type=str, default=None)
parser.add_argument('--read-mo', default=False, action='store_true')
parser.add_argument('--keep-blank', default=False, action='store_true', help='whether or not keep blank entries')

if __name__ == '__main__':
    args = parser.parse_args()
    with Path(__file__).parent.joinpath('default.yml') as fp:
        if fp.exists():
            with Path(__file__).parent.joinpath('default.yml') as fp:
                args = merge_yml(fp, args, parser.parse_args(['']))

pof = initializePOFile(args.locale)
pofiles = []
for target in args.target_dir.glob('*.po'):
    with target.open('br') as f:
        pofiles += [polib.pofile(f, encoding='utf-8')]
if args.read_mo:
    for target in args.target_dir.glob('*.mo'):
        with target.open('br') as f:
            pofiles += [polib.mofile(f, encoding='utf-8')]

for p in pofiles:
    for m in p: 
        if m.string != '' or args.keep_blank:
            pof.append(
                msgid=m.id,
                msgstr=m.string,
                occurrences=m.locations,
                tcomment=m.user_comments,
                msgctxt=m.context)

if len(pof) > 0:
    if not args.output.parent.exists():
        args.output.parent.mkdir(parents=True)
    if args.output.suffix == '.po':
        pof.save(f)
    elif args.output.suffix == '.mo':
        pof.save_as_mofile(f)