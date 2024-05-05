#! /usr/bin/env python3
# encoding: utf-8
import pandas as pd
from pathlib import Path
from typing import Optional
import argparse
import numpy as np
import polib
import warnings
import lxml.etree as ET
from functions import (
    update_with_older_po,
    merge_yml,
    initializePOFile
    )
from datetime import datetime

default_output_path = Path('text/MB2BL-JP.po')
# *_functions.xml?

parser = argparse.ArgumentParser()
parser.add_argument(
    '--vanilla_modules',
    nargs='*', default=None,
    help=f'module names what you want to read.')
parser.add_argument(
    '--output', type=Path, default=default_output_path,
    help=f'output file path. Default = {str(default_output_path)}')
parser.add_argument(
    '--pofile', type=Path,
    default=None,
    help=f'older .PO file path. the original text will be merged and updated with this if exists. Default: what you specified in--output with suffix "-old.po"')
parser.add_argument(
    '--only-diff', type=bool, default=False,
    help='whether or not set blank at each untranslated entry. Default: False')
parser.add_argument(
    '--mb2dir', type=Path,
    default=None,
    help='to specify Mount and Blade II installation folder')
parser.add_argument(
    '--langshort',
    type=str, default=None,
    help='language folder name what you want to read')
parser.add_argument(
    '--locale',
    default=None,
    type=str
)
parser.add_argument(
    '--distinct',
    default=None,
    action='store_true'
)
parser.add_argument('--all-fuzzy', default=False, action='store_true')
parser.add_argument('--legacy-id', default=False, action='store_true')
parser.add_argument('--duplication-in-comment', default=False, action='store_true')
parser.add_argument('--drop-multiplayer', default=None, action='store_true')
parser.add_argument('--dont-evaluate-facial', default=False, action='store_true')

def main():
    df_new = read_xmls(args, how_join='outer')
    dup = check_duplication(df_new)

    df_new.to_excel(f'text/MB2BL-{args.langshort}.xlsx', index=False)

    df_new = escape_for_po(df_new, ['text_EN', f'text_{args.langshort}_original'])
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
    df_new[f'text_{args.langshort}_original'] = df_new[f'text_{args.langshort}_original'].fillna('')
    df_new = df_new.reset_index(drop=True)

    if args.distinct:
        print("Dropping duplicated IDs")
        # TODO: この辺がクソ遅い, たぶん row-wise な処理の実装がアレ
        duplicates = df_new[['id', 'file', 'module']].assign(
            locations=lambda d: (d['module'] + '/' + d['file']).astype(str)
        ).groupby('id').agg(
            {
                'locations': [lambda locs: [(x, 0) for x in locs], lambda locs: len(locs)]
            }
        ).reset_index()
        duplicates.columns = ['id', 'locations', 'duplication']
        df_new = drop_duplicates(df_new, compare_module=True, compare_file=True)
        df_new = df_new.merge(duplicates, on='id', how='left')
        if args.duplication_in_comment:
            df_new = df_new.assign(
                notes=lambda d: np.where(d['duplication'] > 1, [','.join([x for x in [note, f"""{ndup} ID duplications"""] if x != '']) for note, ndup in zip(d['notes'], d['duplication']) ], d['notes']))

    new_pof = initializePOFile('ja_JP')
    if args.only_diff:
        for i, r in df_new.iterrows():
            new_pof.append(
                polib.POEntry(
                    msgid=r['id'],
                    flags=['fuzzy']
                )
            )
    else:
        for i, r in df_new.iterrows():
            new_pof.append(
                polib.POEntry(
                    msgid=r['id'],
                    msgstr = r[f'text_{args.langshort}_original'],
                    tcomment='' if r['notes'] == '' else '\n'.join([r['notes']]),
                    occurrences=r['locations'],
                    flags=['fuzzy']
                )
            )
    if args.pofile.exists():
        if args.pofile.suffix == '.po':
            old_po = polib.pofile(args.pofile, encoding='utf-8')
        elif args.pofile.suffix == '.mo':
            old_po = polib.mofile(args.pofile, encoding='utf-8')
        else:
            old_po = None
        if old_po is None:
            warnings.warn('Old translation file path may be misspecified!')
        else:
            new_one = update_with_older_po(old_po, new_pof, args.all_fuzzy, ignore_facial=False, legacy_id=args.legacy_id)
    else:
        print('Old PO file not found. merging is skipped')
        new_one = new_pof

    df_new = df_new.set_index('id')

    with args.output as fp:
        if fp.exists():
            backup_path = fp.parent.joinpath(
                f"""{fp.with_suffix('').name}-{datetime.now().strftime("%Y-%m-%dT%H%M%S")}.po"""
            )
            fp.rename(backup_path)
            print(f"""old file is renamed to {backup_path.name}""")
        new_one.save(fp)
        print(f'''WRITE AT: {args.output}''')


def read_xmls(args:argparse.Namespace, how_join='left')->pd.DataFrame:
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
                xml = ET.parse(fp)
                if(xml.find('strings') is not None):
                    print(f"reading {args.langshort} file: {fp}")
                    d[args.langshort] += [pd.DataFrame(
                        [(x.attrib['id'], x.attrib['text']) for x in xml.findall('strings/string')],
                        columns=['id', f'text_{args.langshort}_original']
                        ).assign(file=fp.name, module=module)
                    ]
        for fp in dp.glob('*.xml'):
            if not args.drop_multiplayer or (module, fp.name) not in MULTIPLATERS:
                xml = ET.parse(fp)
                if(xml.find('strings') is not None):
                    print(f"reading English file: {fp}")
                    d['EN'] += [pd.DataFrame(
                        [(x.attrib['id'], x.attrib['text']) for x in xml.findall('strings/string')],
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


def escape_for_po(df:pd.DataFrame, columns: str)->pd.DataFrame:
    for c in columns:
        df[c] = df[c].str.replace('%', '%%', regex=False)
    return df


def drop_duplicates(
        df:pd.DataFrame,
        compare_module:bool=False,
        compare_file:bool=False,
        col_module:str='module',
        col_file:str='file',
        module_order:Optional[list[str]]=None,
        file_order:Optional[list[str]]=None
    )->pd.DataFrame:
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


if __name__ == '__main__':

    args = parser.parse_args()
    with Path(__file__).parent.joinpath('default.yml') as fp:
        if fp.exists():
            args = merge_yml(fp, args, parser.parse_args())
    if args.pofile is None:
        args.pofile = Path(args.output.parent).joinpath(f"MB2BL-{args.langshort}.po")
    print(args)
    print(args.pofile)
    main()
