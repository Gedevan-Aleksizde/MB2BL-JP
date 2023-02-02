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
    get_localization_entries, get_default_lang,
    po2pddf_easy, pddf2po
    )
from babel.messages.pofile import read_po, write_po

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
parser.add_argument('--drop-id', default=False, action='store_true')
parser.add_argument('--distinct', default=True, action='store_true')
parser.add_argument('--mb2dir', type=Path, default=mb2dir)


if __name__ == '__main__':
    args = parser.parse_args()
    print(args)
    if args.outdir is None:
        args.outdir = Path(f'ModLangs/{args.target_module}')
        with args.outdir.joinpath(f'ModuleData/Languages/{args.langshort}') as fp:
            if not fp.exists():
                fp.mkdir(parents=True)

# TODO: 念のためオリジナルの言語フォルダも探索させる
# TODO: ID がなかったらどうしようもない
# 一旦無理やりハッシュから生成してみるか?

d_mod = get_localization_entries(args, auto_id=True)
d_default = get_default_lang(args.mb2dir, args.modules, args.langshort)

d_new = d_mod.merge(d_default[['id', 'text']], on='id', how='left').assign(
    text=lambda d: np.where(d['text'].isna(), d['text_EN'], d['text']),
    updated=lambda d: ~d['text'].isna()
)

# TODO: match by string

if args.distinct:
    d_new = d_new.groupby('id').last().reset_index()
d_new = d_new[['id', 'text_EN', 'text', 'file', 'attr', 'updated', 'missing_id']]
d_new.to_excel(args.outdir.joinpath(f'strings_{args.target_module}.xlsx'), index=False)



catalog = pddf2po(d_new)
with args.outdir.joinpath(f'strings_{args.target_module}.po').open('bw') as f:
    write_po(f, catalog)
