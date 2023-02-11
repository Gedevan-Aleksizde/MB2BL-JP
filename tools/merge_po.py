#! /usr/bin/env python3
# encoding: utf-8

import argparse
from pathlib import Path
from babel import Locale # Babel
from babel.messages.pofile import read_po, write_po
from babel.messages.mofile import read_mo, write_mo
from babel.messages.catalog import Catalog, Message
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument('target_dir', type=Path)
parser.add_argument('--output', type=Path, default=Path(f'merege-{datetime.now().strftime("%Y-%m-%dT%H-%M-%S")}.po'))
parser.add_argument('--locale', type=str, default='ja_JP')
parser.add_argument('--read-mo', default=False, action='store_true')

if __name__ == '__main__':
    args = parser.parse_args()

catalog = Catalog(Locale.parse(args.locale))

catalogs = []
for target in args.target_dir.glob('*.po'):
    with target.open('br') as f:
        catalogs += [read_po(f)]
if args.read_mo:
    for target in args.target_dir.glob('*.mo'):
        with target.open('br') as f:
            catalogs += [read_mo(f)]

for c in catalogs:
    for m in c: 
        if m.id != '':
            catalog.add(
                id=m.id,
                string=m.string,
                locations=m.locations,
                user_comments=m.user_comments,
                context=m.context)

if len(catalog) > 0:
    if not args.output.parent.exists():
        args.output.parent.mkdir(parents=True)
    with args.output.open('bw') as f:
        if args.output.suffix == '.po':
            write_po(f, catalog)
        elif args.output.suffix == '.mo':
            write_mo(f, catalog)