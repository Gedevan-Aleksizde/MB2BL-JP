#! /usr/bin/env python3
# encoding: utf-8
import argparse
from pathlib import Path
import warnings
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from babel import Locale # Babel
from babel.messages.pofile import read_po, write_po
from babel.messages.mofile import read_mo, write_mo
from babel.messages.catalog import Catalog
import regex
import hashlib

control_char_remove = regex.compile(r'\p{C}')
match_public_id = regex.compile(r'^(.+?/.+?/.+?)/.*$')
match_file_name_id = regex.compile(r'^.+?/(.+?)/.+?/.*$')
match_internal_id = regex.compile(r'^.+?/.+?/(.+?)/.*$')
match_prefix_id = regex.compile(r'^\[.+?\](.*)$')

def public_po(catalog, drop_id):
    # TODO: VERRRYY DIRTY!!!!!
    a = dict()
    for l in catalog:
        if l.id != '':
            newkey = (match_public_id.sub(r'\1', l.id) , match_file_name_id.sub(r'\1', l.id))
            newval = catalog._messages[(l.id, match_file_name_id.sub(r'\1', l.id))]
            if drop_id:
                newval.string = match_prefix_id.sub(r'\1', newval.string)
            a[newkey] = newval
            l.id = newkey[0] 
    catalog._message = a
    return catalog


def po2pddf(catalog, drop_prefix_id=True):
    """
    input:
    return: `pandas.DataFrame` which contains `id` and `text` columns
    """
    d = pd.DataFrame(
        [(x.id, x.string, ' '.join(x.user_comments)) for x in catalog if x.id != ''], columns=['id', 'text', 'note']
        )
    d = pd.concat([d, d['id'].str.split('/', expand=True)], axis=1).drop(
        columns='id'
        ).rename(
            columns={0: 'module', 1: 'file', 2: 'id'}
            )
    d['text'] = d['text'].str.replace('%%', '%')
    d['id'] = d['id'].str.replace('%%', '%')
    if drop_prefix_id:
        d['text'] = [match_prefix_id.sub(r'\1', x) for x in d['text']]
    return d

def po2pddf_easy(catalog, drop_prefix_id=True):
    """
    input:
    return: `pandas.DataFrame` which contains `id` and `text` columns
    """
    d = pd.DataFrame(
        [(x.id, x.string, ' '.join(x.user_comments)) for x in catalog if x.id != ''], columns=['id', 'text', 'note']
        )
    internal_id = regex.compile('(^.+?)/(.+?)$')
    d['text'] = d['text'].str.replace('%%', '%')
    d['id'] = d['id'].str.replace('%%', '%')
    d['id'] = [internal_id.sub(r'\1', x) for x in d['id']]
    if drop_prefix_id:
        d['text'] = [match_prefix_id.sub(r'\1', x) for x in d['text']]
    return d


def pddf2po(df, with_id=True, distinct=True, locale=None, id_text_col='text', text_col='text'):
    """
    input: `pandas.DataFrame` which contains `id` and `text` columns
    """
    if locale is None:
        locale = Locale.parse('ja_JP')
    if distinct:
        df_unique = df.groupby('id').last().reset_index()
        if df.shape[0] != df_unique.shape[0]:
            warnings.warn(f'{df.shape[0] - df_unique.shape[0]} duplicated IDs are dropped!', UserWarning)
    else:
        df_unique = df
    del df
    catalog = Catalog(locale)
    if with_id:
        df_unique[text_col] = [ f'[{r["id"]}]{r[text_col]}' for _, r in df_unique.iterrows()]
    if 'updated' in df_unique.columns:
        for _, r in df_unique.iterrows():
            catalog.add(r['id'] + '/' + r[id_text_col], r[text_col], flags=[] if r['updated'] else ['fuzzy'])
    else:
        for _, r in df_unique.iterrows():
            catalog.add(r['id'] + '/' + r[id_text_col], r[text_col])
    return catalog


def removeannoyingchars(string, remove_id=False):
    # TODO: against potential abusing of control characters
    string = string.replace('\u3000', ' ')  # why dare you use zenkaku blank?? 
    string = control_char_remove.sub('', string)
    if remove_id:
        string = regex.sub(r'^\[.+?\](.*)$', r'\1', string)
    return string


def get_text_entries(args, auto_id=True):
    ds = []
    module_data_dir = args.mb2dir.joinpath(f'Modules/{args.target_module}/ModuleData')
    print(f'reading xml files from {module_data_dir}')
    for file in module_data_dir.rglob('./*.xml'):
        if file.relative_to(module_data_dir).parts[0].lower() != 'languages':            
            print(file.relative_to(module_data_dir))
            with file.open('r', encoding='utf-8') as f:
                xml = BeautifulSoup(f, features='lxml-xml')
            any_missing = False
            for attr_name in ['text', 'name']:
                xml_entries = xml.find_all(attrs={attr_name: True})
                # xml_entries = xml.select(f'.{attr_name}')
                print(f'''{len(xml_entries)} {attr_name} attributes found''')
                if len(xml_entries) > 0:
                    d = pd.DataFrame({'text_EN': [x[attr_name] for x in xml_entries]}).assign(
                            id = lambda d: np.where(
                                d['text_EN'].str.contains(r'^\{=(.+?)\}.*$', regex=True),
                                d['text_EN'].str.replace(r'^\{=(.+?)\}.*$', r'\1', regex=True),
                                ''
                            ),
                            text_EN = lambda d: d['text_EN'].str.replace(r'^\{=.+?\}(.*)$', r'\1', regex=True),
                        ).assign(attr = attr_name, file = file.name)
                    d['id'] == np.where(d['id'].str.contains(r'^\{=(.+?)\}$', regex=True), d['id'], '')
                    d = d.assign(missing_id = lambda d: (d['id'] == '!') | (d['id'] == '') | (d['id'] == '*'))
                    n_missing = d['missing_id'].sum()
                    if n_missing > 0:
                        warnings.warn(f"""There are {n_missing} missing IDs out of {d.shape[0]} in {file.name}. Action: {"auto assign" if auto_id else "keep" }""", UserWarning)
                        any_missing = True
                        #if drop_id:
                        #    d = d.loc[lambda d: ~((d['id'] == '!') | (d['id'] == '') | (d['id'] == '*'))]
                        if auto_id:
                            d = d.assign(
                                id=lambda d: np.where(
                                    d['missing_id'],
                                    [f'{args.id_prefix}' + hashlib.sha256(text.encode()).hexdigest()[-5:] for text in d['text_EN']],  # TODO
                                    d['id']
                                    )
                                )
                            for (i, r), string in zip(d.iterrows(), xml_entries):
                                if r['missing_id']:
                                    string[attr_name] = "{=" + r['id'] + "}" + r['text_EN']
                    ds += [d]
            if auto_id and any_missing:
                outfp = args.outdir.joinpath(f'ModuleData/{file.relative_to(module_data_dir)}')
                if not outfp.parent.exists():
                    outfp.parent.mkdir(parents=True)
                with outfp.open('w', encoding='utf-8') as f:
                    f.writelines(xml.prettify(formatter='minimal'))
    if len(ds) == 0:
        d = None
    else:
        d = pd.concat(ds)
    return d


def get_default_lang(args, distinct=True, text_col='text'):
    d_defaults = []
    for m in args.modules:
        print(f'LOADING {m} Module...')        
        for fp in args.mb2dir.joinpath(f'Modules/{m}/ModuleData/Languages/{args.langshort}/').glob('*.xml'):
            if fp.name != 'language_data.xml':
                print(fp)
                with fp.open('r', encoding='utf-8') as f:
                    xml = BeautifulSoup(f, features='lxml-xml')
                strings = xml.find('strings')
                if strings is not None:
                    print(fp.name)
                    d = pd.DataFrame(
                        [(x['id'], x['text'] ) for x in strings.find_all('string')],
                        columns = ['id', text_col]
                    ).assign(file = fp.name, module=m)
                    d_defaults += [d]
    if len(d_defaults) > 0:
        d_default = pd.concat(d_defaults)
        if distinct:
            d_default = d_default.groupby('id').last().reset_index()
    else:
        d_default = None
    return d_default


def read_xmls(args):
    d = dict()
    d['EN'] = []
    d[args.langto] = []
    for module in args.modules:
        dp = args.mb2dir.joinpath('Modules').joinpath(module).joinpath("ModuleData/Languages")
        for fp in dp.joinpath(args.langto).glob("*.xml"):
            print(fp)
            with fp.open('r', encoding='utf-8') as f:
                xml = BeautifulSoup(f, features='lxml-xml')
            if(xml.find('strings') is not None):
                d[args.langto] += [pd.DataFrame(
                    [(x.get('id'), x.get('text')) for x in xml.find('strings').find_all('string')],
                    columns=['id', f'text_{args.langto}_original']
                    ).assign(file=fp.name, module=module)
                ]
        for fp in dp.glob('*.xml'):
            with fp.open('r', encoding='utf-8') as f:
                xml = BeautifulSoup(f, features='lxml-xml')
            if(xml.find('string') is not None):
                d['EN'] += [pd.DataFrame(
                    [(x.get('id'), x.get('text')) for x in xml.find('strings').find_all('string')],
                    columns=['id', f'text_EN']
                    ).assign(file=fp.name, module=module)
                    ]
    d['EN'] = pd.concat(d['EN'])
    d['EN'] = d['EN'].assign(text_EN = lambda d: d['text_EN'].str.replace('[\u00a0\u180e\u2007\u200b\u200f\u202f\u2060\ufeff]', '', regex=True))
    d[args.langto] = pd.concat(d[args.langto])
    d[args.langto][f'text_{args.langto}_original'] = d[args.langto][f'text_{args.langto}_original'].str.replace('[\u00a0\u180e\u2007\u200b\u200f\u202f\u2060\ufeff]', '', regex=True)
    d[args.langto]['file'] = d[args.langto]['file'].str.replace(r'^(.+)-jpn\.xml', r'\1.xml', regex=True)

    d_bilingual = d['EN'].merge(d[args.langto], on=['id', 'file', 'module'], how='left')
    d_bilingual = d_bilingual[
        ['module', 'file', 'id', 'text_EN'] + [x for x in d_bilingual.columns if (x[:5] == 'text_' and x[-2:] != 'EN')]
    ].sort_values(['id', 'file'])
    print(f'new text has {d_bilingual.shape[0]} entries')
    return d_bilingual


def check_duplication(df_bilingual):
    duplicated_id = df_bilingual[['id', 'text_EN']].groupby(['id']).agg({'text_EN': [pd.Series.nunique, 'count']}).reset_index()
    duplicated_id.columns = ['id', 'unique', 'duplicates']
    duplicated_id = duplicated_id.loc[lambda d: (d['unique'] > 1) | (d['duplicates'] > 1)]
    if duplicated_id.shape[0] > 1:
        warnings.warn(
            f'''{duplicated_id.loc[lambda d: d['duplicates'] > 1].shape[0]} pairs of duplicated IDs,
            {duplicated_id.loc[lambda d: d['unique'] > 1].shape[0]} pairs of entries of that have even wrong strings.''',
            UserWarning
        )
    df_bilingual = df_bilingual.merge(
        duplicated_id[['id', 'duplicates', 'unique']].drop_duplicates(), on='id', how='left'
        ).assign(
            duplicates = lambda d: np.where(d['duplicates'].isna(), 0, d['duplicates']),
            unique = lambda d: np.where(d['unique'].isna(), 0, d['unique']),
        )
    n_dup = df_bilingual.loc[lambda d: d['duplicates'] > 1].shape[0]
    if n_dup > 0:
        warnings.warn(f'''{n_dup} entries have duplicated ID!''', UserWarning)
    return df_bilingual


def escape_for_po(df, columns):
    for c in columns:
        df[c] = df[c].str.replace('%', '%%', regex=False)
    return df


def update_with_older_po(old_catalog, new_catalog):
    for l in new_catalog:
        if l.id != '':
            old_message = old_catalog[l.id]
            if old_message is not None:
                old_message.string = match_public_id.sub(r'\1', old_message.string)
                if old_message.string != '':
                    new_catalog[l.id].string = old_message.string
                    new_catalog[l.id].user_comments=[] if old_message is None else old_message.user_comments
    # update on public id if not matched
    old_catalog_fuzzy = Catalog(Locale.parse('ja_JP'))
    for l in old_catalog:
        _ = old_catalog_fuzzy.add(
            id=match_public_id.sub(r'\1', l.id),
            string=l.string,
            user_comments=l.user_comments
        )
    for l in new_catalog:
        if l.id != '':
            old_message = old_catalog_fuzzy[match_public_id.sub(r'\1', l.id)]
            if old_message is not None and old_message.string != '' and old_catalog[l.id] is None:
                new_catalog[l.id].string = old_message.string
                new_catalog[l.id].user_comments = l.user_comments
                new_catalog[l.id].flags = ['fuzzy']
    return new_catalog
