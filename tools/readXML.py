#! /usr/bin/env python3
# encoding: utf-8
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import argparse
import numpy as np
import regex
from babel import Locale # Babel
from babel.messages.pofile import read_po, write_po
from babel.messages.catalog import Catalog

control_char_remove = regex.compile(r'\p{C}')
# TODO: excelの廃止
mb2dir = Path('C:\Program Files (x86)\Steam\steamapps\common\Mount & Blade II Bannerlord')

modules = [
    'Native',
    'SandBox',
    'MultiPlayer',
    'CustomBattle',
    'SandBoxCore',
    'StoryMode',
    'BirthAndDeath'
    ]

langs = ['JP']
# *_functions.xml?


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('modules', nargs='*', default=modules)
    parser.add_argument('--output', type=Path, default=Path('text'))
    args = parser.parse_args()

d = dict()
d['EN'] = []
for lang in langs:
    d[lang] = []
    for module in args.modules:
        dp = mb2dir.joinpath('Modules').joinpath(module).joinpath("ModuleData/Languages")
        for fp in dp.joinpath(lang).glob("*.xml"):
            print(fp)
            with fp.open('r', encoding='utf-8') as f:
                xml = BeautifulSoup(f, features='lxml-xml')
            if(xml.find('strings') is not None):
                d[lang] += [pd.DataFrame(
                    [(x.get('id'), x.get('text')) for x in xml.find('strings').find_all('string')],
                    columns=['id', f'text_{lang}_original']
                    ).assign(file=fp.name, module=module)
                ]
        for fp in dp.glob('*.xml'):
            with fp.open('r', encoding='utf-8') as f:
                xml = BeautifulSoup(f, featues='lxml-xml')
            if(xml.find('string') is not None):
                d['EN'] += [pd.DataFrame(
                    [(x.get('id'), x.get('text')) for x in xml.find('strings').find_all('string')],
                    columns=['id', f'text_EN']
                    ).assign(file=fp.name, module=module)
                    ]
d['EN'] = pd.concat(d['EN'])
d['EN'] = d['EN'].assign(text_EN = lambda d: d['text_EN'].str.replace('[\u00a0\u180e\u2007\u200b\u200f\u202f\u2060\ufeff]', '', regex=True))
for lang in langs:
    d[lang] = pd.concat(d[lang])
    d[lang][f'text_{lang}_original'] = d[lang][f'text_{lang}_original'].str.replace('[\u00a0\u180e\u2007\u200b\u200f\u202f\u2060\ufeff]', '', regex=True)
# TODO: do you really want to use control letters?
d['JP']['file'] = d['JP']['file'].str.replace(r'^(.+)-jpn\.xml', r'\1.xml', regex=True)
d_bilingual = d['EN'].merge(d['JP'], on=['id', 'file', 'module'], how='left')
d_bilingual = d_bilingual[
    ['module', 'file', 'id', 'text_EN'] + [x for x in d_bilingual.columns if (x[:5] == 'text_' and x[-2:] != 'EN')]
].sort_values(['id', 'file'])
print(f'new text has {d_bilingual.shape[0]} entries')

duplicated_id = d_bilingual[['id', 'text_EN']].groupby(['id']).agg({'text_EN': [pd.Series.nunique, 'count']}).reset_index()
duplicated_id.columns = ['id', 'unique', 'duplicates']
duplicated_id = duplicated_id.loc[lambda d: (d['unique'] > 1) | (d['duplicates'] > 1)]
if duplicated_id.shape[0] > 1:
    print(
        f'''WARNING: {duplicated_id.loc[lambda d: d['duplicates'] > 1].shape[0]} pairs of duplicated IDs,
    {duplicated_id.loc[lambda d: d['unique'] > 1].shape[0]} pairs of entries of that have even wrong strings.''')
d_bilingual = d_bilingual.merge(
    duplicated_id[['id', 'duplicates', 'unique']].drop_duplicates(), on='id', how='left'
    ).assign(
        duplicates = lambda d: np.where(d['duplicates'].isna(), 0, d['duplicates']),
        unique = lambda d: np.where(d['unique'].isna(), 0, d['unique']),
    )
d_bilingual.to_excel('text/duplicataion.xlsx', index=False)
n_dup = d_bilingual.loc[lambda d: d['duplicates'] > 1].shape[0]
if n_dup > 0:
    print(
        f'''WARNING: {n_dup} entries have duplicated ID!'''
    )

fp = Path('text/languages-old.xlsx')
if fp.exists():
    d_old = pd.read_excel(fp)
    cols = ['module', 'file', 'id'] + [x for x in d_old if x[:5] == 'text_']
    if 'notes' in d_old.columns:
        cols += ['notes']
    d_old = d_old[cols]
    n_new_entries = d_bilingual.merge(d_old, on=['module', 'file', 'id'], how='inner').shape[0]
    d_bilingual =  d_bilingual.merge(
        d_old.rename(columns={
            f'text_EN': 'text_EN_old',
            f'text_{lang}_original': f'text_{lang}_original_old'}),
        on=['module', 'file', 'id'],
        how='left'
        )
    if d_bilingual.shape[0] - n_new_entries == 0:
        print('No entries missing')
    else:
        print(f'{d_bilingual.shape[0] - n_new_entries} entries are not matched with the old data')
    d_bilingual = d_bilingual[[c for c in cols + ['text_EN_old', f'text_{lang}_original_old'] if c in d_bilingual.columns]].assign(
            updated_en=lambda d: d['text_EN'] != d['text_EN_old'],
            updated_jp=lambda d: d['text_JP_original'] != d['text_JP_original_old']
            )
d_bilingual.to_excel('text/languages.xlsx', index=False)

d_escaped = d_bilingual.assign(text_EN=lambda d: d['text_EN'].str.replace('%', '%%', regex=False))
catalog_en = Catalog(Locale.parse('en_US'))
for i, row in d_escaped.fillna('').iterrows():
    _ = catalog_en.add(
            id=row['module'] + '__' + row['id'] + '__' + row['text_EN'],
            string=row[f'text_EN'],
            user_comments=row['notes']
        )
with Path(f"text/translation-en.po").open('bw') as f:
    write_po(fileobj=f, catalog=catalog_en)
for lang in langs:
    d_escaped[f'text_{lang}'] = d_escaped[f'text_{lang}'].str.replace('%', '%%', regex=False)
    d_escaped[f'text_{lang}_original'] = d_escaped[f'text_{lang}_original'].str.replace('%', '%%', regex=False)
    catalog_original = Catalog(Locale.parse('ja_JP'))
    catalog_new = Catalog(Locale.parse('ja_JP'))
    catalog_en = Catalog(Locale.parse('en_US'))
    for i, row in d_escaped.fillna('').iterrows():
        _ = catalog_new.add(
            id='/'.join(row[['module', 'file', 'id', 'text_EN']]),
            string=row[f'text_{lang}'],
            user_comments=row['notes']
            )
        _ = catalog_original.add(
            id='/'.join(row[['module', 'file', 'id', 'text_EN']]),
            string=row[f'text_{lang}_original'],
            user_comments=row['notes']
        )
        _ = catalog_en.add(
            id='/'.join(row[['module', 'file', 'id', 'text_EN']]),
            string=row[f'text_EN'],
            user_comments=row['notes']
        )
    with args.output.joinpath(f'MB2BL-{lang}.po').open('bw') as f:
        write_po(fileobj=f, catalog=catalog_new)
    with args.output.joinpath(f'MB2BL-{lang}-original.po').open('bw') as f:
        write_po(fileobj=f, catalog=catalog_original)