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
from babel.messages.catalog import Catalog
import warnings
from functions import read_xmls, check_duplication, escape_for_po, update_with_older_po
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
    args = parser.parse_args()
    if args.old is None:
        args.old = Path(args.output.parent).joinpath(f"{args.output.with_suffix('').name}-old.po")



df_new = read_xmls(args)
dup = check_duplication(df_new)

df_new.to_excel(f'text/MB2BL-{args.langto}.xlsx', index=False)

df_new = escape_for_po(df_new, ['text_EN', f'text_{args.langto}_original'])
df_new = df_new.assign(
        id_original=lambda d: d['id'],
        id_short=lambda d: d['module'] + '/' + d['file'] + '/' + d['id'],
        id=lambda d: d['module'] + '/' + d['file'] + '/' + d['id'] + '/' + d['text_EN']
        )
df_new[f'text_{args.langto}_original'] = df_new[f'text_{args.langto}_original'].fillna('')
df_new = df_new.reset_index(drop=True)

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
            # string=(f'[{r["id_original"]}]' if args.with_id else '') + r[f'text_{args.langto}_original']
            string = r[f'text_{args.langto}_original']
        )


if args.old.exists():
    with args.old.open('br') as f:
        old_catalog = read_po(f)
    new_one = update_with_older_po(old_catalog, new_catalog)
else:
    new_one = new_catalog

##########
## !!! Babel.messages.catalog.Catalog indexing HARDLY WORK AFTER THIS !!!!
##########

df_new = df_new.set_index('id')
for l in new_one:
    if l.id != '':
        new_one[l.id].context = df_new.loc[l.id]['file']
    
##########
with args.output as fp:
    if fp.exists():
        backup_path = fp.parent.joinpath(
            f"""{fp.with_suffix('').name}-{datetime.now().strftime("%Y-%m-%dT%H-%M-%S")}.po"""
        )
        fp.rename(backup_path)
        print(f"""old file is renamed to {backup_path.name}""")
    with fp.open('bw') as f:
        write_po(f, new_one)
    print(f'''WRITE AT: {args.output}''')
