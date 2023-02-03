#! /usr/bin/env python3

import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path
import regex
import argparse
import numpy as np
from functions import (
    read_xmls, check_duplication, escape_for_po,
    update_with_older_po,
    get_text_entries, get_default_lang,
    po2pddf_easy, pddf2po
    )
from babel.messages.pofile import read_po, write_po
from datetime import datetime

mb2dir = Path('C:\Program Files (x86)\Steam\steamapps\common\Mount & Blade II Bannerlord')
modules = [
    'SandBoxCore',
    'SandBox',
    'CustomBattle',
    'MultiPlayer',
    'StoryMode',
    'Native',
    'CorrectLocalizationJP-Text',
    'Dummy'
]


parser = argparse.ArgumentParser()
parser.add_argument('target_module', type=str)
parser.add_argument('--outdir', type=Path, default=None)
parser.add_argument('--modules', nargs='*', default=modules)
parser.add_argument('--langshort', type=str, default='JP')
parser.add_argument('--langid', type=str, default='日本語')
parser.add_argument('--with-id', default=False, action='store_true')
parser.add_argument('--merge-modules', default=False, action='store_true')
parser.add_argument('--distinct', default=False, action='store_true')
parser.add_argument('--mb2dir', type=Path, default=mb2dir)
parser.add_argument('--id-prefix', type=str, default=None)


if __name__ == '__main__':
    args = parser.parse_args()
    print(args)
    if args.outdir is None:
        args.outdir = Path(f'ModLangs/{args.target_module}')
        with args.outdir.joinpath(f'ModuleData/Languages/{args.langshort}') as fp:
            if not fp.exists():
                fp.mkdir(parents=True)
    if args.id_prefix is None:
        args.id_prefix = args.target_module

# TODO: ID がなかったらどうしようもない
# 無理やりハッシュから生成してみるか?

d_mod = get_text_entries(args, auto_id=True)

args_ = argparse.Namespace(**vars(args))
args_.langshort = ''
args_.modules = [args.target_module]
tmp1 = get_default_lang(args_, distinct=args_.distinct, text_col='text_EN')
args_.langshort = 'EN'
tmp2 = get_default_lang(args_, distinct=args_.distinct, text_col='text_EN')

d_mod_lang = pd.concat([tmp1, tmp2]) if not (tmp1 is None and tmp2 is None) else None


if d_mod is None:
    d_mod = d_mod_lang
elif d_mod_lang is not None:
    d_mod = d_mod.merge(d_mod_lang, on='id', how='left').assign(
        file=lambda d: np.where(d['file_x'] == '', d['file_y'], d['file_x']),
        text_EN=lambda d: np.where(d['text_EN_x'] == '', d['text_EN_y'], d['text_EN_x'])
    )[['id', 'text_EN', 'file']]
else:
    pass

if d_mod is None:
    raise('No text entry found!')
else:
    if args.merge_modules:
        print("get default language files...")
        d_default = get_default_lang(args)
        d_mod = d_mod.merge(d_default[['id', 'text']], on='id', how='left').assign(
            text=lambda d: np.where(d['text'].isna(), d['text_EN'], d['text']),
            updated=lambda d: ~d['text'].isna()
        )



# TODO: match by string

if args.distinct:
    d_mod = d_mod.groupby('id').last().reset_index()
d_mod = d_mod[d_mod.columns.intersection(set(['id', 'text_EN', 'text', 'file', 'attr', 'updated', 'missing_id']))]

with args.outdir.joinpath(f'strings_{args.target_module}.xlsx') as fp:
    if fp.exists():
        backup_fp = fp.parent.joinpath(
            f"""{fp.with_suffix('').name}-{datetime.now().strftime("%Y-%M-%dT%H-%M-%S")}.xlsx"""
        )
        print(f"""old file is renamed to {backup_fp}""")
        fp.rename(backup_fp)
    d_mod.to_excel(fp, index=False)

catalog = pddf2po(d_mod, with_id=args.with_id, id_text_col='text_EN', text_col='text_EN', distinct=args.distinct)

with args.outdir.joinpath(f'strings_{args.target_module}.po') as fp:
    if fp.exists():
        backup_fp = fp.parent.joinpath(
            f"""{fp.with_suffix('').name}-{datetime.now().strftime("%Y-%M-%dT%H-%M-%S")}.po"""
        )
        print(f"""old file is renamed to {backup_fp}""")
        fp.rename(backup_fp)
    with fp.open('bw') as f:
        write_po(f, catalog)
