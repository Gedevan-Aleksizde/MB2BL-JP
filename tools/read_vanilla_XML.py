#! /usr/bin/env python3
# encoding: utf-8
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import argparse
import numpy as np
import regex
from babel import Locale # Babel
from babel.messages.pofile import read_po, write_po
from babel.messages.mofile import read_mo
from babel.messages.catalog import Catalog
import warnings
from functions import read_xmls, check_duplication, escape_for_po, update_with_older_po, drop_duplicates
from datetime import datetime

# from tools.functions import read_xmls, check_duplication, escape_for_po, update_with_older_po

modules = [
    'Native',
    'SandBox',
    'MultiPlayer',
    'CustomBattle',
    'SandBoxCore',
    'StoryMode',
    'BirthAndDeath'
    ]
default_output_path = Path('text/MB2BL-JP.po')
# *_functions.xml?


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--modules',
        nargs='*', default=modules,
        help=f'module names what you want to read. Default = {", ".join(modules)} ')
    parser.add_argument(
        '--output', type=Path, default=default_output_path,
        help=f'output file path. Default = {str(default_output_path)}')
    parser.add_argument(
        '--old', type=Path,
        default=Path('text/MB2BL-JP.po'),
        help=f'older .PO file path. the original text will be merged and updated with this if exists. Default: what you specified in--output with suffix "-old.po"')
    parser.add_argument(
        '--only-diff', type=bool, default=False,
        help='whether or not set blank at each untranslated entry. Default: False')
#    parser.add_argument(
#        '--with-id', default=True,
#        help='whether or not prefix text ID to each untranslated text entry. Default: True',
#        action='store_true'
#    )
    parser.add_argument(
        '--mb2dir', type=Path,
        default=Path('C:\Program Files (x86)\Steam\steamapps\common\Mount & Blade II Bannerlord'),
        help='to specify Mount and Blade II installation folder')
    parser.add_argument(
        '--langto',
        type=str, default='JP',
        help='language folder name what you want to read')
    parser.add_argument(
        '--locale',
        default='ja_JP',
        type=str
    )
    parser.add_argument(
        '--no-distinct',
        default=False,
        action='store_true'
    )
    parser.add_argument('--all-fuzzy', default=False, action='store_true')
    parser.add_argument('--legacy-id', default=False, action='store_true')
    parser.add_argument('--duplication-in-comment', default=False, action='store_true')
    args = parser.parse_args()
    if args.old is None:
        args.old = Path(args.output.parent).joinpath(f"{args.output.with_suffix('').name}-old.po")



df_new = read_xmls(args, how_join='outer')
dup = check_duplication(df_new)

df_new.to_excel(f'text/MB2BL-{args.langto}.xlsx', index=False)

df_new = escape_for_po(df_new, ['text_EN', f'text_{args.langto}_original'])
if args.legacy_id:
    df_new = df_new.assign(
            id_original=lambda d: d['id'],
            id_short=lambda d: d['module'] + '/' + d['file'] + '/' + d['id'],
            id=lambda d: d['id'] + '/' + d['text_EN']
            )
else:
    df_new = df_new.assign(
            id_original=lambda d: d['id'],
            id=lambda d: d['id'] + '/' + d['text_EN']
            )
df_new[f'text_{args.langto}_original'] = df_new[f'text_{args.langto}_original'].fillna('')
df_new = df_new.reset_index(drop=True)

if not args.no_distinct:
    print("Dropping duplicated IDs")
    # TODO: この辺がクソ遅い, たぶん row-wise な処理の実装がアレ
    duplicates = df_new[['id', 'file', 'module']].assign(
        location=lambda d: d['module'] + '/' + d['file']
    ).groupby('id').agg(
        {
            'location': [lambda locs: [(x, 0) for x in locs], lambda locs: len(locs)]
        }
    ).reset_index()
    duplicates.columns = ['id', 'locations', 'duplication']
    df_new = drop_duplicates(df_new, compare_module=True, compare_file=True)
    df_new = df_new.merge(duplicates, on='id', how='left')
    if args.duplication_in_comment:
        df_new = df_new.assign(
            notes=lambda d: np.where(d['duplication'] > 1, [','.join([x for x in [note, f"""{ndup} ID duplications"""] if x != '']) for note, ndup in zip(d['notes'], d['duplication']) ], d['notes']))


new_catalog = Catalog(Locale.parse('ja_JP'))
if args.only_diff:
    for i, r in df_new.iterrows():
        _ = new_catalog.add(
            id=r['id']
        )
else:
    for i, r in df_new.iterrows():
        _ = new_catalog.add(
            id=r['id'],
            string = r[f'text_{args.langto}_original'],
            user_comments=[] if r['notes'] == '' else [r['notes']],
            locations=r['locations']
        )

if args.old.exists():
    if args.old.suffix == '.po':
        with args.old.open('br') as f:
            old_catalog = read_po(f)
    elif args.old.suffix == '.mo':
        with args.old.open('br') as f:
            old_catalog = read_mo(f)
    else:
        old_catalog = None
    if old_catalog is None:
        warnings.warn('Old translation file path may be misspecified!')
    else:
        new_one = update_with_older_po(old_catalog, new_catalog, args.all_fuzzy, legacy_id=args.legacy_id)
else:
    print('Old PO file not found. merging is skipped')
    new_one = new_catalog


##########
## !!! Babel.messages.catalog.Catalog indexing HARDLY WORK AFTER THIS !!!!
##########

df_new = df_new.set_index('id')
for l in new_one:
    if l.id != '':
        new_one[l.id].context = f'''{df_new.loc[l.id]['module']}/{df_new.loc[l.id]['file']}'''

##########
with args.output as fp:
    if fp.exists():
        backup_path = fp.parent.joinpath(
            f"""{fp.with_suffix('').name}-{datetime.now().strftime("%Y-%m-%dT%H%M%S")}.po"""
        )
        fp.rename(backup_path)
        print(f"""old file is renamed to {backup_path.name}""")
    with fp.open('bw') as f:
        write_po(f, new_one)
    print(f'''WRITE AT: {args.output}''')
