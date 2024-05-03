#! /usr/bin/env python3
# encoding: utf-8
import argparse
from pathlib import Path
import yaml
import warnings
import pandas as pd
import numpy as np
from babel import Locale # Babel
from babel.messages.pofile import read_po, write_po
from babel.messages.mofile import read_mo, write_mo
from babel.messages.catalog import Catalog
import regex
import hashlib
from datetime import datetime
import copy

control_char_remove = regex.compile(r'\p{C}')
match_public_id_legacy = regex.compile(r'^(.+?/.+?/.+?)/.*$')
match_file_name_id_legacy = regex.compile(r'^.+?/(.+?)/.+?/.*$')
match_internal_id_legacy = regex.compile(r'^.+?/.+?/(.+?)/.*$')
match_prefix_id = regex.compile(r'^\[.+?\](.*)$')

match_public_id = regex.compile(r'^(.+?)/.+$')
match_string = regex.compile(r'^.+?/(.+)$')

def merge_yml(fp:Path, args:argparse.Namespace, default:argparse.Namespace)->argparse.Namespace:
    with fp.open('r', encoding='utf-8') as f:
        yml = yaml.load(f, Loader=yaml.Loader)
        for k in yml.keys():
            if yml[k] == 'None':
                yml[k] = None
            if k in ['outdir', 'mb2dir', 'merge_with_gettext'] and yml[k] is not None:
                yml[k] = Path(yml[k])
    d_args = vars(args)
    d_default = vars(default)
    d_args_updated = {k: v for k, v in d_args.items() if v is not None}
    d_args_extra = {k: v for k, v in d_default.items() if k not in yml.keys()}
    yml.update(d_args_extra)
    yml.update(d_args_updated)
    d_args = yml
    args = argparse.Namespace(**d_args)
    if args.filename_sep_version is None:
       args.filename_sep_version = '1.2' 
    if args.filename_sep_version not in ['1.0', '1.1', '1.2']:
        warnings.warn('The value for --filename-sep-version is irregular! set to `1.2`')
        args.filename_sep_version = '1.2'
    args.filename_sep = '_' if args.filename_sep_version == '1.2' else '-'
    return args


def get_catalog_which_has_corrected_babel_fake_id(catalog_with_fake_id: Catalog, simplify=True) -> Catalog:
    # WHY BABEL USES FAKE ID???
    catalog_with_correct_id = Catalog(Locale.parse('ja_JP'))
    if simplify:
        for true_id in catalog_with_fake_id._messages:
            _ = catalog_with_correct_id.add(
                id = catalog_with_fake_id._messages[true_id].id,
                string =  catalog_with_fake_id._messages[true_id].string,
                user_comments = catalog_with_fake_id._messages[true_id].user_comments,
                flags = catalog_with_fake_id._messages[true_id].flags,
                locations = catalog_with_fake_id._messages[true_id].locations
            )
        for true_id in catalog_with_fake_id._messages:
                catalog_with_correct_id[true_id[0]].context = catalog_with_fake_id._messages[true_id].context
    else:
        for true_id in catalog_with_fake_id._messages:
            _ = catalog_with_correct_id.add(
                id = true_id,
                string =  catalog_with_fake_id._messages[true_id].string,
                user_comments = catalog_with_fake_id._messages[true_id].user_comments,
                flags = catalog_with_fake_id._messages[true_id].flags,
                locations = catalog_with_fake_id._messages[true_id].locations
            )
        for true_id in catalog_with_fake_id._messages:
                catalog_with_correct_id[true_id[0]].context = catalog_with_fake_id._messages[true_id].context
    return catalog_with_correct_id


def public_po(catalog: Catalog) -> Catalog:
    # TODO: copy of metadata
    # TODO: distinction
    catalog = copy.deepcopy(catalog)
    for true_id in catalog._messages:
        catalog._messages[true_id].id = match_public_id.sub(r'\1', true_id)
    return catalog



def po2pddf(catalog:Catalog, drop_prefix_id:bool=True, drop_excessive_cols:bool=True, legacy:bool=False) -> pd.DataFrame:
    """
    input:
    return: `pandas.DataFrame` which contains `id`, `file`, `module`, `text`, `text_EN ,`notes`, `flags` columns
    """
    d = pd.DataFrame(
        [(x.id, x.string, x.user_comments, x.flags, x.locations, x.context) for x in catalog if x.id != ''],
        columns=['id', 'text', 'notes', 'flags', 'locations', 'context']
    )
    d = pd.concat([d, d['id'].str.split('/', expand=True)], axis=1).drop(
            columns='id'
        )
    if legacy:
        d = d.rename(
            columns={0: 'module', 1: 'file', 2: 'id'}
        )
        d['context'] = d['file']
    else:
        d = d.rename(
            columns={0: 'id'}
        )
        d = d.rename(columns={1: 'text_EN'})
        d = d.assign(duplication=lambda d: [len(x) for x in d['locations']])
        d['text_EN'] = d['text_EN'].str.replace('%%', '%')
    d['text'] = d['text'].str.replace('%%', '%')
    d['id'] = d['id'].str.replace('%%', '%')
    if drop_prefix_id:
        d['text'] = [match_prefix_id.sub(r'\1', x) for x in d['text']]
    if drop_excessive_cols:
        d = d[[x for x in d.columns if x in ['id', 'text', 'text_EN', 'notes', 'flags', 'locations', 'context', 'file', 'module', 'duplication']]]
    return d


def po2pddf_easy(catalog: Catalog, with_id=False) -> pd.DataFrame:
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
    if with_id:
        d['text'] = '[' + d['id'] + ']' +  d['text']
    return d


def pddf2po(
    df: pd.DataFrame, with_id:bool=True, make_distinct:bool=True, regacy_mode:bool=False, locale:str=None, col_id_text:str='text', col_text:str='text',
    col_locations:str=None, col_context:str=None, col_comments:str=None, col_flags:str=None,
    )->Catalog:
    """
    input: `pandas.DataFrame` which contains `id` and `text` columns
    """
    if locale is None:
        locale = Locale.parse('ja_JP')
    if make_distinct:
        df_unique = df.groupby('id').last().reset_index()
        if df.shape[0] != df_unique.shape[0]:
            warnings.warn(f'{df.shape[0] - df_unique.shape[0]} duplicated IDs are dropped!', UserWarning)
    else:
        df_unique = df
    del df
    df_unique[col_text] = np.where(df_unique[col_text].isna() | df_unique[col_text].isnull(), '', df_unique[col_text])
    catalog = Catalog(locale)
    if with_id:
        df_unique[col_text] = [ f'[{r["id"]}]{r[col_text]}' for _, r in df_unique.iterrows()]
    # I shouldn't have used Babel.
    print(f'col_flags={col_flags}, {col_flags is None}')

    if not regacy_mode:
        def format_arg(dic: dict)->dict:
            dic['id'] = f"""{dic['id']}/{dic[col_id_text]}"""
            dic['string'] = dic[col_text]
            if col_flags is None:
                dic['flags'] = ['fuzzy']
            else:
                dic['flags'] = dic.get(col_flags)
            if col_locations is not None:
                dic['locations'] = [(str(x), 0) for x in dic.get(col_locations)]
            dic['user_comments'] = dic.get(col_comments, '') if type(dic.get(col_comments, '')) is list else []
            dic['context'] = dic.get(col_context)
            return dic
    else:
        def format_arg(dic: dict)->dict:
            dic['id'] = f"""{dic['id']}/{dic[col_id_text]}"""
            dic['string'] = dic[col_text]
            if col_flags is None:
                pass
            else:
                dic['flags'] = [] if dic.get('updated') else ['fuzzy']
            dic['locations'] = [(dic.get(col_locations), 0)]
            dic['user_comments'] = [dic.get(col_comments, '')]
            dic['context'] = dic.get(col_context)
            return dic            
    d = [format_arg(dict(r)) for _, r in df_unique.iterrows()]
    keys = {'id', 'string', 'flags'}
    if col_comments is not None:
        keys.add('user_comments')
    if col_context is not None:
        keys.add('context')
    if col_locations is not None:
        keys.add('locations')
    current_keys = list(d[0].keys())
    _ = [dic.pop(k, None) for dic in d for k in current_keys if k not in keys]
    for r in d:
        catalog.add(**r)
    return catalog

def removeannoyingchars(string: str, remove_id=False) -> str:
    # TODO: against potential abusing of control characters
    string = string.replace('\u3000', ' ')  # why dare you use zenkaku blank?? 
    string = control_char_remove.sub('', string)
    if remove_id:
        string = regex.sub(r'^\[.+?\](.*)$', r'\1', string)
    return string


def export_id_text_list(input_pofile:Path, output:Path)->None:
    """
    read pofile and export as csv with id and text columns. mainly used for compare with misassigned IDs in the third-party mods
    """
    with input_pofile.open('br') as f:
        catalog = read_po(f)
    d = pd.DataFrame([(x.id) for x in catalog if x.id != ''], columns=['id'])
    d['text_EN'] = d['id'].str.replace(r'^(.+?)/(.+?)$', r'\2', regex=True)
    d['id'] = d['id'].str.replace(r'^(.+?)/.+?$', r'\1', regex=True)
    if output.exists():
        backup_path = output.parent.joinpath(
            f"""vanilla-id-{datetime.now().strftime("%Y-%m-%dT%H%M%S")}.csv"""
        )
        print(f'{output} already exists. the older file is moved to {backup_path}')
        output.rename(backup_path)
    d.to_csv(output, index=False)
