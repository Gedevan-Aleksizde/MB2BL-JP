#! /usr/bin/env python3
# encoding: utf-8

import argparse
from pathlib import Path
from babel import Locale # Babel
from babel.messages.pofile import read_po, write_po
from babel.messages.mofile import read_mo
from babel.messages.catalog import Catalog
from datetime import datetime
import regex

parser = argparse.ArgumentParser()
parser.add_argument('target', type=Path)
parser.add_argument('--output', type=Path, default=Path(f'MB2BL-{datetime.now().strftime("%Y-%m-%dT%H-%M-%S")}.po'))

if __name__ == '__main__':
    args = parser.parse_args()

if args.target.exists():
    with args.target.open('br') as f:
        if args.target.suffix == '.mo':
            catalog = read_mo(f)
        elif args.target.suffix == '.po':
            catalog = read_po(f)
        else:
            raise(f'{args.target} extension is wrong')
else:
    raise(f'{args.target} not found!')


match_internal_id = regex.compile(r'^.+?/.+?/(.+?)/(.*$)')

for m in catalog:
    if m.id != '':
        m.id = match_internal_id.sub(r'\1/\2', m.id)

if not args.output.parent.exists():
    args.output.parent.mkdir()
with args.output.open('bw') as f:
    write_po(f, catalog)
