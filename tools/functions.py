#! /usr/bin/env python3
# encoding: utf-8
import argparse
from pathlib import Path
import yaml
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


def drop_duplicates(df: pd.DataFrame, compare_module=False, compare_file=False, col_module='module', col_file='file', module_order=None, file_order=None) -> pd.DataFrame:
    if module_order is None:
        module_order = [
            'Native',
            'SandBox',
            'MultiPlayer',
            'CustomBattle',
            'SandBoxCore',
            'StoryMode',
            'BirthAndDeath'
        ]
    module_order = {k: v for k, v in zip(module_order, range(len(module_order)))}
    default_module_order = len(module_order) + 1
    if file_order is None:
        file_order = [
            'std_global_strings',
            'std_module_string'
        ]
    file_order = {k: v for k, v in zip(range(len(file_order)), file_order)}
    default_file_order = len(file_order) + 1
    if compare_module:
        df = df.assign(module_order=lambda d: [module_order.get(x, default_module_order) for x in d[col_module]])
    if compare_file:
        df = df.assign(
            file_order=lambda d: [file_order.get(x, default_file_order) for x in d[col_file]]
        )
    df = df.sort_values(
        ['id'] + (['module_order'] if compare_module else []) + ['file_order'] if compare_file else []
    ).groupby(['id']).last().reset_index().drop(columns=(['module_order'] if compare_module else []) + ['file_order'] if compare_file else [] )
    return df


def removeannoyingchars(string: str, remove_id=False) -> str:
    # TODO: against potential abusing of control characters
    string = string.replace('\u3000', ' ')  # why dare you use zenkaku blank?? 
    string = control_char_remove.sub('', string)
    if remove_id:
        string = regex.sub(r'^\[.+?\](.*)$', r'\1', string)
    return string


def get_text_entries(args: pd.DataFrame, auto_id=True) -> pd.DataFrame:
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
                # xml_entries = xml.find_all(attrs={attr_name: True})
                xml_entries = xml.find_all(name=regex.compile('[^string]'), attrs={attr_name: True})
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


def get_default_lang(args: argparse.Namespace, distinct=True, text_col='text') -> pd.DataFrame:
    d_defaults = []
    for m in args.default_modules:
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


def read_xmls(args: argparse.Namespace, how_join='left') -> pd.DataFrame:
    # TODO: 例外的な処理がこんなに複雑になるのはバニラだけ?
    MULTIPLATERS = [
        ("Native", "std_mpbadges.xml"),
        ("Native", "std_mpcharacters_xml.xml"),
        ("Native", "std_mpclassdivisions_xml.xml"),
        ("Native", "std_mpitems_xml.xml"),
        ("Native", "std_multiplayer_strings_xml.xml")
    ]
    d = dict()
    d['EN'] = []
    d[args.langshort] = []
    for module in args.vanilla_modules:
        dp = args.mb2dir.joinpath('Modules').joinpath(module).joinpath("ModuleData/Languages")
        for fp in dp.joinpath(args.langshort).glob("*.xml"):
            if not args.drop_multiplayer or (module, fp.name) not in MULTIPLATERS:
                with fp.open('r', encoding='utf-8') as f:
                    xml = BeautifulSoup(f, features='lxml-xml')
                if(xml.find('strings') is not None):
                    print(f"reading {args.langshort} file: {fp}")
                    d[args.langshort] += [pd.DataFrame(
                        [(x.get('id'), x.get('text')) for x in xml.find('strings').find_all('string')],
                        columns=['id', f'text_{args.langshort}_original']
                        ).assign(file=fp.name, module=module)
                    ]
        for fp in dp.glob('*.xml'):
            if not args.drop_multiplayer or (module, fp.name) not in MULTIPLATERS:
                with fp.open('r', encoding='utf-8') as f:
                    xml = BeautifulSoup(f, features='lxml-xml')
                if(xml.find('strings') is not None):
                    print(f"reading English file: {fp}")
                    d['EN'] += [pd.DataFrame(
                        [(x.get('id'), x.get('text')) for x in xml.find('strings').find_all('string')],
                        columns=['id', f'text_EN']
                        ).assign(file=fp.name, module=module)
                        ]
    d['EN'] = pd.concat(d['EN'])
    d['EN'] = d['EN'].assign(text_EN = lambda d: d['text_EN'].str.replace('[\u00a0\u180e\u2007\u200b\u200f\u202f\u2060\ufeff]', '', regex=True))
    d[args.langshort] = pd.concat(d[args.langshort])
    d[args.langshort][f'text_{args.langshort}_original'] = d[args.langshort][f'text_{args.langshort}_original'].str.replace('[\u00a0\u180e\u2007\u200b\u200f\u202f\u2060\ufeff]', '', regex=True)
    # d[args.langshort]['file'] = d[args.langshort]['file'].str.replace(r'^(.+)_jpn\.xml', r'\1.xml', regex=True)
    d[args.langshort] = d[args.langshort].rename(columns={'file': f'file_{args.langshort}', 'module': f'module_{args.langshort}'})
    d_bilingual = d['EN'].merge(d[args.langshort], on=['id'], how=how_join)
    d_bilingual = d_bilingual.assign(
        file=lambda d: np.where(d['file'].isna(), 'Hardcoded, ' + d[f'file_{args.langshort}'], d['file']),
        module=lambda d: np.where(d['module'].isna(), 'Hardcoded, ' + d[f'module_{args.langshort}'], d['module']))
    # Who can assume that the original text ID is incomplete??
    if how_join:
        d_bilingual = d_bilingual.assign(
            notes=lambda d: np.where(d['text_EN'].isna(), 'The original text cannot available, assumed hardcoded', ''),
            text_EN=lambda d: np.where(d['text_EN'].isna(), d[f'text_{args.langshort}_original'], d['text_EN']))
    else:
        d_bilingual['notes'] = ''
    d_bilingual = d_bilingual[
        ['module', 'file', 'id', 'text_EN', 'notes'] + [x for x in d_bilingual.columns if (x[:5] == 'text_' and x[-2:] != 'EN')]
    ].sort_values(['id', 'file'])
    print(f'new text has {d_bilingual.shape[0]} entries')

    return d_bilingual


def check_duplication(df_bilingual:pd.DataFrame)->pd.DataFrame:
    # TODO: 仕様が古い?
    duplicated_id = df_bilingual[['id', 'text_EN']].groupby(['id']).agg({'text_EN': [pd.Series.nunique, 'count']}).reset_index()
    duplicated_id.columns = ['id', 'unique', 'duplicates']
    duplicated_id = duplicated_id.loc[lambda d: (d['unique'] > 1) | (d['duplicates'] > 1)]
    if duplicated_id.shape[0] > 1:
        warnings.warn(
            f'''{duplicated_id.loc[lambda d: d['duplicates'] > 1].shape[0]} pairs of duplicated IDs,
            {duplicated_id.loc[lambda d: d['unique'] > 1].shape[0]} pairs of entries of that have even wrong strings.''',
            UserWarning
        )
    df_distinct = df_bilingual.merge(
        duplicated_id[['id', 'duplicates', 'unique']].drop_duplicates(), on='id', how='left'
        ).assign(
            duplicates = lambda d: np.where(d['duplicates'].isna(), 0, d['duplicates']),
            unique = lambda d: np.where(d['unique'].isna(), 0, d['unique']),
        )
    n_dup = df_distinct.loc[lambda d: d['duplicates'] > 1].shape[0]
    if n_dup > 0:
        warnings.warn(f'''{n_dup} entries have duplicated ID!''', UserWarning)
    return df_distinct


def escape_for_po(df: pd.DataFrame, columns: str) -> pd.DataFrame:
    for c in columns:
        df[c] = df[c].str.replace('%', '%%', regex=False)
    return df


def update_with_older_po(old_catalog: Catalog, new_catalog: Catalog, all_fuzzy=False, ignore_facial=True, legacy_id=False) -> Catalog:
    # I shouldn't have used Babel
    if legacy_id:
        for l in new_catalog:
            if l.id != '':
                old_message = old_catalog[l.id]
                if old_message is not None:
                    old_message.string = match_public_id_legacy.sub(r'\1', old_message.string)
                    if old_message.string != '':
                        new_catalog[l.id].string = old_message.string
                        new_catalog[l.id].user_comments = old_message.user_comments
                else:
                    print(f"error: irregular catlog ID={l.id}")
        # update on public id if not matched
        old_catalog_fuzzy = Catalog(Locale.parse('ja_JP'))
        for l in old_catalog:
            _ = old_catalog_fuzzy.add(
                id=match_public_id_legacy.sub(r'\1', l.id),
                string=l.string,
                user_comments=l.user_comments,
                flags=l.flags,
                context=l.context,
                locations=l.locations
            )
        n_match = 0
        for l in new_catalog:
            if l.id != '':
                old_message = old_catalog_fuzzy[match_public_id_legacy.sub(r'\1', l.id)]
                if old_message is not None and old_message.string != '' and old_catalog[l.id] is None:
                    n_match += 1
                    new_catalog[l.id].string = old_message.string
                    new_catalog[l.id].user_comments += old_message.user_comments
                    new_catalog[l.id].flags = ['fuzzy'] if all_fuzzy or 'fuzzy' in old_message.flags else []
        print(f'Updated {n_match} entries matched on public ID')
    else:
        suffix_facial = regex.compile("(\[ib:.+\]|\[if:.+\])")  # against v1.2 updates
        # WHY BABEL USES FAKE ID???
        old_catalog_correct_id = get_catalog_which_has_corrected_babel_fake_id(old_catalog)
        n_match = 0
        for l in new_catalog:
            if l.id != '':
                old_message = old_catalog_correct_id[suffix_facial.sub("", l.id)] if ignore_facial else old_catalog_correct_id[l.id]
                if old_message is not None:
                    if old_message.string != '':
                        new_catalog[l.id].string = old_message.string
                        new_catalog[l.id].user_comments += old_message.user_comments
                        new_catalog[l.id].flags = ['fuzzy'] if all_fuzzy or 'fuzzy' in old_message.flags else []
                        n_match += 1
        total_entries = len([m for m in new_catalog if m.id != ''])
        print(f'Updated {n_match}/{total_entries} entries matched by both the internal ID')
        if n_match == total_entries:
            print('all entries are matched')
        else:
            # update on public ID if the original text changed or somewhat get hardcoded
            old_catalog_fuzzy = Catalog(Locale.parse('ja_JP'))
            for l in old_catalog_correct_id:
                #ahoshine = match_public_id.sub(r'\1', l.id)
                #print(f'{ahoshine}: {l.string}')
                _ = old_catalog_fuzzy.add(
                    id=match_public_id.sub(r'\1', l.id),
                    string=l.string,
                    user_comments=l.user_comments,
                    flags=l.flags | set('fuzzy') if all_fuzzy or 'fuzzy' in l.flags else set(),
                    context=l.context
                )
            old_catalog_fuzzy = get_catalog_which_has_corrected_babel_fake_id(old_catalog_fuzzy)
            n_match = 0
            for l in new_catalog:
                if l.id != '':
                    old_message = old_catalog_fuzzy[match_public_id.sub(r'\1', l.id)]
                    if old_message is not None and old_message.string != '' and old_catalog[l.id] is None and old_message.string != l.string:
                        new_catalog[l.id].string = old_message.string
                        new_catalog[l.id].user_comments += old_message.user_comments
                        new_catalog[l.id].flags = ['fuzzy']
                        n_match += 1
            print(f'Updated {n_match} entries matched by the public ID')
    return new_catalog


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
