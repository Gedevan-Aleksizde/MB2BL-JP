#! /usr/bin/env python3

import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path
import yaml
import regex
import argparse
import numpy as np
from babel.messages.pofile import read_po, write_po
from babel.messages.mofile import read_mo, write_mo
from datetime import datetime
import warnings
from functions import (
    read_xmls, check_duplication, escape_for_po,
    update_with_older_po,
    get_text_entries, get_default_lang,
    po2pddf_easy, pddf2po, po2pddf
    )

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
parser.add_argument('target_module', type=str, help='target module folder name')
parser.add_argument('--outdir', type=Path, default=None, help='output folder default is `./Mods`')
parser.add_argument('--langshort', type=str, default='JP')
parser.add_argument('--langid', type=str, default='日本語')
parser.add_argument(
    '--merge-by-id', default=False, action='store_true',
    help="<NOT RECOMMENDED> merge with original text by IDs. NOTE: the same ID means this text can't show because the localzation engine's failre"
    )
parser.add_argument(
    '--drop-original-language', default=False, action='store_true', help='suppress to merge the own language folder')
parser.add_argument('--default-modules', nargs='*', default=modules, help='to specify vanilla module names. This is used for --merge-with-id')
parser.add_argument('--merge_with_mo', type=Path, default=Path("text/MB2BL-JP.mo")) # TODO: 複数のファイルを参照 
parser.add_argument('--distinct', default=False, action='store_true', help='drop duplicated IDs the last loaded entries are left per ID')
parser.add_argument('--fill-english', default=False, action='store_true', help='to fill the translated text with original (English) text')
parser.add_argument('--with-id', default=False, action='store_true', help='to add ID to translated text')
parser.add_argument('--mb2dir', type=Path, default=mb2dir, help='MB2 install folder')
parser.add_argument('--id-prefix', type=str, default=None)


if __name__ == '__main__':
    args = parser.parse_args()
    if args.outdir is None:
        args.outdir = Path(f'Mods/{args.target_module}')
        with args.outdir.joinpath(f'ModuleData/Languages/{args.langshort}') as fp:
            if not fp.exists():
                fp.mkdir(parents=True)
    if args.id_prefix is None:
        args.id_prefix = args.target_module
    print(args)

# TODO: REFACTORING!!!

# TODO: ID がなかったらどうしようもない
# 無理やりハッシュから生成してみるか?
# TODO: たまに UTF-16で保存してくるやつがいる...
# TODO: name は必ずしもテキストではなくなにかを参照している
# TODO: 元テキスト変えてるやつも多いのでIDで紐づけはデフォでやらないように

print("get default language files...")
d_default = get_default_lang(args).assign(duplicated_with_vanilla = True)

# from ModuleData except Languages folder
d_mod = get_text_entries(args, auto_id=True)

def get_mod_languages(args):
    ds = []
    ds_translation = []
    module_data_dir = args.mb2dir.joinpath(f'Modules/{args.target_module}/ModuleData')
    print(f'reading xml files from {module_data_dir}')
    for file in module_data_dir.rglob('./*.xml'):
        # TODO: 元のmodの配置がめちゃくちゃだったらどうしようもない
        if file.relative_to(module_data_dir).parts[0].lower() == 'languages':
            if args.drop_original_language and file.relative_to(module_data_dir.joinpath('Languages')).parts[0].lower() == args.langshort.lower():
                print(file.relative_to(module_data_dir))
                with file.open('r', encoding='utf-8') as f:
                    xml = BeautifulSoup(f, features='lxml-xml')
                xml_entries = xml.find_all('string')
                if len(xml_entries) > 0:
                    d = pd.DataFrame(
                        {(x['id'], x['text']) for x in xml_entries},
                        columns=['id', 'text']
                    )
                    d = d.assign(file=file.name)
                    ds_translation += [d]
        else:
            print(file.relative_to(module_data_dir))
            with file.open('r', encoding='utf-8') as f:
                xml = BeautifulSoup(f, features='lxml-xml')
            xml_entries = xml.find_all('string')
            print(f'''{len(xml_entries)} string tag found''')
            if len(xml_entries) > 0:
                d = pd.DataFrame({(x['id'], x['text']) for x in xml_entries}, columns=['id', 'text_EN'])
                d = d.assign(
                    missing_id = lambda d: (d['id'] == '!') | (d['id'] == '') | (d['id'] == '*'),
                    file=file.name)
                n_missing = d['missing_id'].sum()
                if n_missing > 0:
                    warnings.warn(f"""There are {n_missing} missing IDs out of {d.shape[0]} in {file.name}. Action: {"auto assign" if auto_id else "keep" }""", UserWarning)
                    d = d.loc[lambda d: ~d['id'].isna()]
                ds += [d]
    if len(ds) > 0:
        d = pd.concat(ds)
    else:
        d = None
    if len(ds_translation) > 0:
        d_translation = pd.concat(ds_translation)
        d_translation = d_translation.drop_duplicates()
        if d is not None:
            d = d.merge(d_translation, on='id', how='left') 
    return d

d_mod_lang = get_mod_languages(args)

if d_mod is None:
    d_mod = d_mod_lang.assign(missing_id=lambda d: ~d['id'].isna())
elif d_mod_lang is not None:
    d_mod = d_mod.merge(d_mod_lang, on='id', how='outer').assign(
        file=lambda d: np.where(d['file_x'] == '', d['file_y'], d['file_x']),
        text_EN=lambda d: np.where(d['text_EN_x'] == '', d['text_EN_y'], d['text_EN_x'])
    ).drop(columns=['text_EN_x', 'text_EN_y'])
else:
    pass

if d_mod is None:
    raise('No text entry found!')

print(f"""{d_mod.shape[0]} entries found""")

if args.merge_by_id:
    d_mod = d_mod.merge(d_default[['id', 'text', 'duplicated_with_vanilla']], on='id', how='left').assign(
    text=lambda d: np.where(d['text'].isna(), d['text_EN'], d['text']),
    updated=lambda d: ~d['text'].isna()
    )
else:
    d_mod = d_mod.merge(d_default[['id', 'duplicated_with_vanilla']], on='id', how='left')
d_mod['duplicated_with_vanilla'] = d_mod['duplicated_with_vanilla'].fillna(False)

# merge by string
if args.merge_with_mo is not None:
    if args.merge_with_mo.exists():
        with args.merge_with_mo.open('br') as f:
            catalog = read_mo(f)
    elif args.merge_with_mo.with_suffix(".po").exists():
            with args.merge_with_mo.with_suffix(".po").open('br') as f:
                catalog = read_po(f)
    else:
        catalog = None
    if catalog is not None:
        d_po = pd.DataFrame([(m.id, m.string) for m in catalog if m.id != ''], columns=['id', '__text__'])
        match_text_en = r'^.+?/.+?/.+?/(.+?)$'
        match_internal_id = r'^.+?/.+?/(.+?)/.+?$'
        d_po = d_po.assign(
            text_EN=lambda d: d['id'].str.replace(match_text_en, r'\1', regex=True),
            __text__=lambda d: d['__text__'].str.replace(r'^\[.+?\]', '', regex=True),
            id=lambda d: d['id'].str.replace(match_internal_id, r'\1', regex=True)
            )
        d_po = d_po.groupby('id').last().reset_index()
        d_mod = d_mod.merge(d_po[['id', '__text__']], on='id', how='left')
        if 'text' not in d_mod.columns:
            d_mod['text'] = np.nan
        d_mod = d_mod.assign(
            text=lambda d: np.where(d['text'].isna() | (d['text'] == ''), d['__text__'], d['text'] )
        )
        if 'updated' in d_mod.columns:
            d_mod = d_mod.assign(updated=lambda d: d['updated'] | ~d['__text__'].isna())
        else:
            d_mod = d_mod.assign(updated=lambda d: ~d['__text__'].isna())
        d_mod = d_mod.drop(columns=['__text__'])
        if args.distinct:
            d_mod = d_mod.groupby('id').last().reset_index()
        d_mod = d_mod.merge(d_po[['text_EN', '__text__']], on='text_EN', how='left')
        if 'text' not in d_mod.columns:
            d_mod['text'] = np.nan
        d_mod = d_mod.assign(
            text = lambda d: np.where(d['text'].isna() | (d['text'] == ''), d['__text__'], d['text'])
        )
        if args.distinct:
            d_mod = d_mod.groupby('id').last().reset_index()
        if 'updated' in d_mod.columns:
            d_mod = d_mod.assign(updated=lambda d: d['updated'] | ~d['__text__'].isna())
        else:
            d_mod = d_mod.assign(updated=lambda d: ~d['__text__'].isna())
        d_mod = d_mod.drop(columns=['__text__'])
    else:
        warnings.warn(f"{args.merge_with_mo} not found!", UserWarning)


if args.fill_english:
    d_mod = d_mod.assign(
        text=lambda d: np.where((d['text'] == '') | d['text'].isna(), d['text_EN'], d['text'])
    )


if args.distinct:
    d_mod = d_mod.groupby('id').last().reset_index()
d_mod = d_mod[d_mod.columns.intersection(set(['id', 'text_EN', 'text', 'file', 'attr', 'updated', 'missing_id', 'duplicated_with_vanilla']))]

with args.outdir.joinpath(f'strings_{args.target_module}.xlsx') as fp:
    if fp.exists():
        backup_fp = fp.parent.joinpath(
            f"""{fp.with_suffix('').name}-{datetime.now().strftime("%Y-%m-%dT%H-%M-%S")}.xlsx"""
        )
        print(f"""old file is renamed to {backup_fp}""")
        fp.rename(backup_fp)
    d_mod.to_excel(fp, index=False)

d_mod = d_mod.fillna('')
catalog = pddf2po(d_mod, with_id=args.with_id, id_text_col='text_EN', text_col='text', distinct=args.distinct)


with args.outdir.joinpath(f'strings_{args.target_module}.po') as fp:
    if fp.exists():
        backup_fp = fp.parent.joinpath(
            f"""{fp.with_suffix('').name}-{datetime.now().strftime("%Y-%m-%dT%H-%M-%S")}.po"""
        )
        print(f"""old file is renamed to {backup_fp}""")
        fp.rename(backup_fp)
    with fp.open('bw') as f:
        write_po(f, catalog)
