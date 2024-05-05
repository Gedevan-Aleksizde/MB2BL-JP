#! /usr/bin/env python3
# encoding: utf-8

import argparse
from pathlib import Path
import polib
from datetime import datetime
import regex
from functions import po2pddf, pddf2po

parser = argparse.ArgumentParser()
parser.add_argument('target', type=Path)
parser.add_argument('--output', type=Path, default=Path(f'MB2BL-{datetime.now().strftime("%Y-%m-%dT%H%M%S")}.po'))

if __name__ == '__main__':
    args = parser.parse_args()

if args.target.exists():
    with args.target.open('br') as f:
        if args.target.suffix == '.mo':
            pof = polib.pofile(f, encoding='utf-8')
        elif args.target.suffix == '.po':
            pof = polib.mofile(f, encoding='utf-8')
        else:
            raise(f'{args.target} extension is wrong')
else:
    raise(f'{args.target} not found!')


match_internal_id = regex.compile(r'^.+?/.+?/(.+?)/(.*$)')

d = po2pddf(pof, drop_prefix_id=False, legacy=True, drop_excessive_cols=False)
excluding_cols = ['id', 'text', 'notes', 'flags', 'locations', 'context', 'module', 'file']
d['text_EN'] = d[[x for x in d.columns if x not in excluding_cols]].agg(lambda x: '/'.join([y for y in x if y is not None]), axis=1)
d = d[[x for x in d.columns if x in excluding_cols + ['text_EN']]]

d = d.assign(isnative=lambda d: d['module']=='Native').sort_values(['id', 'isnative']).groupby(['id']).last().reset_index().drop(columns=['isnative'])
d = d.assign(
    # notes=lambda d: [''.join(x) for x in  d['notes']],
    # locations=lambda d: [''.join(x) for x in  d['locations']]
    notes='', locations=''
    )
d['locations'] = d['file']
d['flags'] = [['fuzzy'] if 'fuzzy' in x else [] for x in d['flags']]
d = d.assign(text=lambda d: d['text'].str.replace('%', '%%'))

pof_new = pddf2po(d, with_id=False, col_id_text='text_EN', col_locations='locations', col_context='context', col_comments='notes', col_flags='flags')

if not args.output.parent.exists():
    args.output.parent.mkdir()
with args.output as fp:
    if fp.exists():
        backup_path = fp.parent.joinpath(
            f"""{fp.with_suffix('').name}-{datetime.now().strftime("%Y-%m-%dT%H%M%S")}.po"""
        )
        fp.rename(backup_path)
        print(f"""old file is renamed to {backup_path.name}""")
pof_new.save(args.output)
