#! /usr/bin/env python3

import argparse
import yaml
from pathlib import Path
import warnings

import pandas as pd
from bs4 import BeautifulSoup
import regex
import numpy as np
from babel.messages.pofile import read_po, write_po
from babel.messages.mofile import read_mo, write_mo
from datetime import datetime

from functions import (
    read_xmls, check_duplication, escape_for_po,
    update_with_older_po,
    get_default_lang,
    po2pddf_easy, pddf2po, po2pddf,
    drop_duplicates,
    merge_yml
    )
import hashlib

parser = argparse.ArgumentParser()
parser.add_argument('target_module', type=str, help='target module folder name')
parser.add_argument('--outdir', type=Path, default=None, help='output folder default is `./Mods`')
parser.add_argument('--langshort', type=str, default='JP')
parser.add_argument('--langid', type=str, default='日本語')
parser.add_argument('--vanilla-modules', nargs='*', default=None, help='to specify vanilla module names. You can specify other modules if the official translation is BAD. NOTE: this function will work only if the modules contain both English and the target language files')
parser.add_argument(
    '--how-merge', default='string', type=str,
    help="`none`, `string`, `id`, or `both`. how to merge with other translation files. The default is `string` merge by the originla (English) string if default. The latter two values are <NOT RECOMMENDED>.  NOTE: the same ID means this text can't show because the localzation engine's failre"
    )
parser.add_argument('--not-merge-with-vanilla', default=False, action='store_true', help='stop merge with modules specified in `--vanilla-modules`')
parser.add_argument(
    '--drop-original-language', default=False, action='store_true', help='suppress to merge the own language folder')
parser.add_argument(
    '--pofile', type=Path, default=None,
    help='additional translation file. PO or MO file are available. It requires the same format as what this script outputs') # TODO: 複数のファイルを参照 
parser.add_argument('--distinct', default=False, action='store_true', help='drop duplicated IDs the last loaded entries are left per ID')
parser.add_argument('--fill-english', default=False, action='store_true', help='to fill the translated text with original (English) text')
parser.add_argument('--mb2dir', type=Path, default=None, help='MB2 install folder')
parser.add_argument('--autoid-prefix', type=str, default=None)
parser.add_argument('--avoid-vanilla-id', default=False, action='store_true')
parser.add_argument('--keep-redundancies', default=False, action='store_true', help='whether or not add different IDs to entries with same strings')
parser.add_argument('--convert-exclam', default=False, action='store_true')
parser.add_argument('--verbose', default=False, action='store_true')


if __name__ == '__main__':
    args = parser.parse_args()
    with Path(__file__).parent.joinpath('default.yml') as fp:
        if fp.exists():
            args = merge_yml(fp, args, parser.parse_args(['']))
    if args.outdir is None:
        args.outdir = Path(f'Mods/{args.target_module}')
        with args.outdir.joinpath(f'{args.target_module}/ModuleData/Languages/{args.langshort}') as fp:
            if not fp.exists():
                fp.mkdir(parents=True)
    if args.autoid_prefix is None:
        args.autoid_prefix = args.target_module.encode('ascii', errors='ignore').decode().replace(' ', '')
    if not args.how_merge in ['none', 'string', 'id', 'both']:
        warnings.warn(f'--how-merge={args.how_merge} is invalid value! it should be one of `none`, `string`, `id`, or `both`. now `string` used ', UserWarning)
        args.how_merge = 'string'
    if args.pofile is None:
        args.pofile = args.outdir.joinpath(f'{args.target_module}.po')
    print(args)

# TODO: REFACTORING!!!

# TODO: たまに UTF-16で保存してくるやつがいる...
# TODO: 元テキスト変えてるやつも多いのでIDで紐づけはデフォでやらないように
# TODO: Mod作者はまずIDをまともに与えてないという想定で作る
# TODO: =! は何か特別な意味がある?
# TODO: 長い文のマッチングに失敗している?

print("get default language files...")
# d_default = get_default_lang(args).assign(duplicated_with_vanilla = True)

# from ModuleData except Languages folder
# d_mod = get_text_entries(args, auto_id=True)


def extract_text_from_xml(args, complete_id=True, keep_redundancies=False):
    """
    # タグはいろいろあるので翻訳対象の条件づけが正確なのかまだ自信がない
    # TODO: ! とか * とか訳のわからんIDを付けているケースが多い. 何の意味が?
    """
    ds = []
    filters = [
        dict(name='ItemModifier', attrs='name'),
        dict(name='CraftedItem', attrs='name'),
        dict(name='CraftingPiece', attrs='name'),
        dict(name='Item', attrs='name'),
        dict(name='NPCCharacter', attrs='name'),
        dict(name='NPCCharacter', attrs='text'),
        dict(name='Hero', attrs='text'),
        dict(name='Settlement', attrs='name'),
        dict(name='Settlement', attrs='text'),
        dict(name='Faction', attrs='name'),
        dict(name='Faction', attrs='short_name'),
        dict(name='Faction', attrs='text'),
        dict(name='Culture', attrs='name'),
        dict(name='Culture', attrs='text'),
        dict(name='Kingdom', attrs='name'),
        dict(name='Kingdom', attrs='short_name'),
        dict(name='Kingdom', attrs='text'),
        dict(name='Kingdom', attrs='title'),
        dict(name='Kingdom', attrs='ruler_title'),
        dict(name='Concept', attrs='title'),
        dict(name='Concept', attrs='description'),
        dict(name='name', attrs='name'), # TODO: 余計なものまで取得する可能性は?
        dict(name='string', attrs='text')
    ]
    module_data_dir = args.mb2dir.joinpath(f'Modules/{args.target_module}/ModuleData')
    print(f'reading xml files from {module_data_dir}')
    vanilla_ids = pd.read_csv(Path(__file__).parent.joinpath('vanilla-id.csv')).assign(id_used_in_vanilla=True)
    lambda_id = (
        lambda d: np.where(
            d['missing_id'] | d['is_duplicated'],
            [f'{args.autoid_prefix}' + hashlib.sha256((text + str(i)).encode()).hexdigest()[-5:] for i, text in enumerate(d['context'] + d['attr'] + d['text_EN'])],  # TODO
            d['id']
        )
    ) if keep_redundancies else (
        lambda d: np.where(
            d['missing_id'] | d['is_duplicated'],
            [f'{args.autoid_prefix}' + hashlib.sha256(text.encode()).hexdigest()[-5:] for text in d['context'] + d['attr'] + d['text_EN']],  # TODO
            d['id']
        )
    )
    func_check_duplicate = (lambda d: d['n_id'] > 1) if keep_redundancies else (lambda d: (d['n_id'] > 1) & (d['n_id_text'] == 1))
    for file in module_data_dir.rglob('./*.xml'):
        if file.relative_to(module_data_dir).parts[0].lower() != 'languages':            
            print(f"""(not language file) {file.relative_to(module_data_dir)}""")
            with file.open('r', encoding='utf-8') as f:
                xml = BeautifulSoup(f, features='lxml-xml')
            any_missing = False
            for filter in filters:
                xml_entries = xml.find_all(name=filter['name'], attrs={filter['attrs']: True}) # TODO: BSが条件に一致していても取得しないものがある????
                if args.verbose:
                    print(f'''{len(xml_entries)} {filter['attrs']} attributes found in {filter['name']} tags''')
                if len(xml_entries) > 0:
                    d = pd.DataFrame(
                        [(x[filter['attrs']], f'''{filter['name']}.{filter['attrs']}''') for x in xml_entries], columns=['text_EN', 'context']
                        ).assign(
                            id = lambda d: np.where(
                                d['text_EN'].str.contains(r'^\{=(.+?)\}.*$', regex=True),
                                d['text_EN'].str.replace(r'^\{=(.+?)\}.*$', r'\1', regex=True),
                                ''
                            ),
                            text_EN = lambda d: d['text_EN'].str.replace(r'^\{=.+?\}(.*)$', r'\1', regex=True),
                        ).assign(attr = filter['attrs'], file = file.name)
                    if not args.convert_exclam:
                        d = d.loc[lambda df: ~(df['id'] == '!')]
                    d['id'] == np.where(d['id'].str.contains(r'^\{=(.+?)\}$', regex=True), d['id'], '')
                    # TODO: precise id detetion
                    if args.avoid_vanilla_id:
                        d = d.merge(vanilla_ids.rename(columns={'text_EN': 'text_EN_original'}), on='id', how='left')
                        d['id'] = np.where(d['id_used_in_vanilla'] & (d['text_EN'] != d['text_EN_original']), '', d['id'])
                        d = d.drop(columns=['text_EN_original', 'id_used_in_vanilla'])
                        # TODO: 常にバニラと比較するように
                    d = d.assign(missing_id = lambda d: (d['id'].str.contains('^[?!\*]$')) | (d['id'] == '') | (d['id'] == '*'))
                    d = d.merge(vanilla_ids, on=['id', 'text_EN'], how='left')
                    d = d.loc[lambda d: ~d['id_used_in_vanilla'].fillna(False)]
                    n_missing = d['missing_id'].sum()
                    if complete_id:
                        # TODO: 原文重複かつIDが違う/欠損している場合を想定していない
                        check_dup_id = (d if ds == [] else pd.concat(ds + [d])).groupby(['id', 'text_EN']).size().reset_index().rename(columns={0: 'n_id_text'}).merge(
                            (d if ds == [] else pd.concat(ds + [d])).groupby(['id']).size().reset_index().rename(columns={0: 'n_id'}),
                            on='id', how='left'
                        )
                        check_dup_id = check_dup_id.assign(is_duplicated=func_check_duplicate).reset_index()[['id', 'text_EN', 'is_duplicated']]
                        d = d.merge(check_dup_id, on=['id', 'text_EN'], how='left')
                    else:
                        d['is_duplicated'] = False
                    if n_missing > 0 or d['is_duplicated'].sum() > 0:
                        warnings.warn(
                            f"""There are {n_missing} {"missing or reused" if args.avoid_vanilla_id else "missing"} IDs out of {d.shape[0]} in {file.name}. Action: {"auto assign" if complete_id else "keep" }""",
                            UserWarning)
                        warnings.warn(
                            f"""Thee are {d['is_duplicated'].sum()} duplicated IDs out of {d.shape[0]} in {file.name}. Action: {"auto assign" if complete_id else "keep" }""",
                            UserWarning
                        )
                        any_missing = True
                        if complete_id:
                            d = d.assign(id=lambda_id)
                            for (_, r), string in zip(d.iterrows(), xml_entries):
                                if r['missing_id'] | r['is_duplicated']:
                                    string[filter['attrs']] = "{=" + r['id'] + "}" + r['text_EN']
                    ds += [d]
            if complete_id and any_missing:
                outfp = args.outdir.joinpath(f'{args.target_module}/ModuleData/{file.relative_to(module_data_dir)}')
                if not outfp.parent.exists():
                    outfp.parent.mkdir(parents=True)
                with outfp.open('w', encoding='utf-8') as f:
                    f.writelines(xml.prettify(formatter='minimal'))
        else:
            if file.relative_to(module_data_dir).parts[1] == file.name:
                print(f"""(English language file) {file.relative_to(module_data_dir)}""")
                # English Language files
                with file.open('r', encoding='utf-8') as f:
                    xml = BeautifulSoup(f, features='lxml-xml')
                xml_entries = xml.find_all(name='string', attrs={'id': True, 'text': True})
                if len(xml_entries) > 0:
                    d = pd.DataFrame(
                        [(x['id'], x['text'], 'string.text') for x in xml_entries], columns=['id', 'text_EN', 'context']
                    ).assign(attr = 'string', file = file.name)
                    ds += [d]
    if len(ds) == 0:
        d_return = None
    else:
        d_return = pd.concat(ds)
        d_return = d_return.assign(
            text_EN=lambda d: np.where(d['text_EN'] == '', np.nan, d['text_EN'])
        )
    return d_return


def get_mod_languages(args, auto_id=True, check_non_language_folder=False):
    """
    Extract Text from all XML files in target module's ModuleData/Languages

    auto_id: Bool=True, assign IDs automatically if missing

    翻訳対象の言語を取り出す
    # TODO: 元のmodの配置がめちゃくちゃだったらどうしようもない
    # 現時点では, Languages フォルダ上のXMLまたは module_string.xml が言語ファイルで, 逆に取りこぼしもないと仮定
    """
    ds = []
    ds_translation = []
    module_data_dir = args.mb2dir.joinpath(f'Modules/{args.target_module}/ModuleData')
    print(f'reading xml files from {module_data_dir}')
    for file in module_data_dir.rglob('./*.xml'):
        if file.relative_to(module_data_dir).parts[0].lower() == 'languages':
            if not args.drop_original_language and file.relative_to(module_data_dir.joinpath('Languages')).parts[0].lower() == args.langshort.lower():
                print(f"""{file.relative_to(module_data_dir)}""")
                with file.open('r', encoding='utf-8') as f:
                    xml = BeautifulSoup(f, features='lxml-xml')
                xml_entries = xml.find_all('string')
                if len(xml_entries) > 0:
                    d = pd.DataFrame(
                        {(x['id'], x['text']) for x in xml_entries},
                        columns=['id', 'text']
                    )
                    d = d.assign(file=file.name, context='string.text')
                    ds_translation += [d]
        elif check_non_language_folder:
            print(file.relative_to(module_data_dir))
            with file.open('r', encoding='utf-8') as f:
                xml = BeautifulSoup(f, features='lxml-xml')
            xml_entries = xml.find_all('string')
            print(f'''{len(xml_entries)} string tag found''')
            if len(xml_entries) > 0:
                d = pd.DataFrame({(x['id'], x['text']) for x in xml_entries}, columns=['id', 'text_EN'])
                d = d.assign(
                    missing_id = lambda d: (d['id'] == '!') | (d['id'] == '') | (d['id'] == '*'),
                    file=file.name,
                    context='string.text')
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
    else:
        d_translation = None
    if d is not None:
        d = d.assign(
            text_EN=lambda d: np.where(d['text_EN'] == '', np.nan, d['text_EN'])
        )
        if 'text' in d.columns:
            d['text'] = np.where(d['text'] == '', np.nan, d['text'])
    elif d_translation is not None:
        d = d_translation.assign(text_EN=np.nan)
    return d

if not args.mb2dir.joinpath(f'Modules/{args.target_module}').exists():
    raise(f'''{args.mb2dir.joinpath('Modules/').joinpath(args.target_module)} not found!''')

print("---- Detect text from ModuleData ----")
d_mod = extract_text_from_xml(args, complete_id=True, keep_redundancies=args.keep_redundancies)

# TODO: デフォルトのモジュールから EN/Terget 両方取得する

print("---- Extract strings from ModuleData/Lanugages ----")
d_module_lang = get_mod_languages(args)

if d_mod is None:
    d_mod = d_module_lang.assign(missing_id=lambda d: ~d['id'].isna())
elif d_module_lang is not None:
    d_mod = d_mod.merge(d_module_lang, on='id', how='outer').assign(
        file=lambda d: np.where(d['file_y'].isna(), d['file_x'], d['file_y']),
        text_EN=lambda d: np.where(d['text_EN_y'].isna(), d['text_EN_x'], d['text_EN_y']),
        context=lambda d: np.where(d['context_x'].isna(), d['context_y'], d['context_x'])
    ).drop(columns=['text_EN_x', 'text_EN_y', 'file_x', 'file_y', 'context_x', 'context_y'])


if d_mod is None:
    raise('No text entry found!')

if 'text' not in d_mod.columns:
    d_mod = d_mod.assign(text=np.nan)

print(f"""---- {d_mod.shape[0]} entries found ----""")

if args.vanilla_modules is not None and args.vanilla_modules != [''] and not args.not_merge_with_vanilla:
    args.modules=args.vanilla_modules
    df_vanilla_language = read_xmls(args, how_join='outer')
    df_vanilla_language = drop_duplicates(df_vanilla_language)
    if df_vanilla_language.shape[0] > 0:
        df_vanilla_language = df_vanilla_language.rename(
            columns={f'text_{args.langshort}_original': 'text'}
            ).assign(duplicated_with_vanilla = True)
        if args.how_merge in ['string', 'both']:
            tmp = df_vanilla_language[['text_EN', 'text', 'duplicated_with_vanilla']].groupby('text_EN').first().reset_index().loc[lambda d: d['text_EN'] != '']
            d_mod = d_mod.merge(tmp, on='text_EN', how='left').assign(
                text=lambda d: np.where(d['text_x'].isna(), d['text_y'], d['text_x']),
                updated=lambda d: ~d['text'].isna()
                ).drop(columns=['text_x', 'text_y'])
        if args.how_merge in ['id', 'both']:
            tmp = df_vanilla_language[['id', 'text', 'duplicated_with_vanilla']].groupby('id').first().reset_index().loc[lambda d: d['id'] != '']
            d_mod = d_mod.merge(tmp, on='id', how='left').assign(
                text=lambda d: np.where(d['text_x'].isna(), d['text_y'], d['text_x']),
                updated=lambda d: ~d['text'].isna()
                ).drop(columns=['text_x', 'text_y'])
        d_mod['duplicated_with_vanilla'] = d_mod['duplicated_with_vanilla'].fillna(False)
else:
    d_mod['duplicated_with_vanilla'] = False

if 'text' not in d_mod.columns:
    d_mod['text'] = np.nan
if 'updated' not in d_mod.columns:
    d_mod['updated'] = np.nan

# TODO: Mod ですらIDを重複させてくるやつがいる
# TODO: バニラとかぶってるID
# TODO: 結合方法の確認
# TODO: % のエスケープ

# merge with the PO/MO file by the original string
print("---- start to merge ----")
print(args.pofile)
if args.pofile is not None:
    if args.pofile.exists():
        with args.pofile.open('br') as f:
            if args.pofile.suffix == '.mo':
                catalog = read_mo(f)
            elif args.pofile.suffix == '.po':
                catalog = read_po(f)
    elif args.pofile.with_suffix('.po').exists():
            with args.pofile.with_suffix('.po').open('br') as f:
                catalog = read_po(f)
                print(f"{args.pofile.with_suffix('.po')} loaded insteadly")
    else:
        warnings.warn(f'''{args.pofile} not found''')
        catalog = None
    if catalog is not None:
        d_po = pd.DataFrame([(m.id, m.string) for m in catalog if m.id != ''], columns=['id', '__text__'])
        match_text_en = r'^.+?/(.+?)$'
        match_internal_id = r'^(.+?)/.+?$'
        d_po = d_po.assign(
            text_EN=lambda d: d['id'].str.replace(match_text_en, r'\1', regex=True),
            # __text__=lambda d: d['__text__'].str.replace(r'^\[.+?\]', '', regex=True),
            id=lambda d: d['id'].str.replace(match_internal_id, r'\1', regex=True)
            )
        d_po = d_po.groupby('id').last().reset_index()
        if args.how_merge in ['string', 'both']:
            print("merge by English text")
            d_mod = d_mod.merge(d_po[['text_EN', '__text__']], on='text_EN', how='left')
            d_mod = d_mod.assign(
                text=lambda d: np.where(d['text'].isna(), d['__text__'], d['text'] )
            )
            d_mod = d_mod.assign(updated=lambda d: ~d['__text__'].isna())
            d_mod = d_mod.drop(columns=['__text__'])

        if args.how_merge in ['id', 'both']:
            print("merge by the localization IDs")
            d_mod = d_mod.merge(d_po[['id', '__text__']], on='id', how='left')
            d_mod = d_mod.assign(
                text=lambda d: np.where(d['text'].isna(), d['__text__'], d['text'] )
            )
            d_mod = d_mod.assign(updated=lambda d: ~d['__text__'].isna())
            d_mod = d_mod.drop(columns=['__text__'])
        if args.distinct:
            d_mod = d_mod.groupby('id').first().reset_index()
    else:
        warnings.warn(f"{args.pofile} not found!", UserWarning)

if args.fill_english:
    d_mod = d_mod.assign(
        text=lambda d: np.where(d['text'].isna(), d['text_EN'], d['text'])
    )

if args.distinct:
    d_mod = d_mod.groupby('id').last().reset_index()

d_mod = d_mod[d_mod.columns.intersection(
    {'id', 'text_EN', 'text', 'file', 'attr', 'updated', 'missing_id', 'duplicated_with_vanilla','context', 'notes'})]

with args.outdir.joinpath(f'{args.target_module}.xlsx') as fp:
    if fp.exists():
        backup_fp = fp.parent.joinpath(
            f"""{fp.with_suffix('').name}-{datetime.now().strftime("%Y-%m-%dT%H-%M-%S")}.xlsx"""
        )
        print(f"""old file is renamed to {backup_fp}""")
        fp.rename(backup_fp)
    d_mod.to_excel(fp, index=False)

d_mod = d_mod.fillna('')
catalog = pddf2po(
    d_mod, with_id=False, distinct=args.distinct,
    col_id_text='text_EN', col_text='text', col_comments='notes', col_context='context', col_locations='file')

with args.outdir.joinpath(f'{args.target_module}.po') as fp:
    if fp.exists():
        backup_fp = fp.parent.joinpath(
            f"""{fp.with_suffix('').name}-{datetime.now().strftime("%Y-%m-%dT%H-%M-%S")}.po"""
        )
        print(f"""old file is renamed to {backup_fp}""")
        fp.rename(backup_fp)
    with fp.open('bw') as f:
        write_po(f, catalog)
