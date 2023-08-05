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
    merge_yml,
    export_id_text_list
    )
import hashlib

parser = argparse.ArgumentParser()
parser.add_argument('target_module', type=str, help='target module folder name')
parser.add_argument('--outdir', type=Path, default=None, help='output folder default is `./Mods`')
parser.add_argument('--langshort', type=str, default='JP')
parser.add_argument('--langid', type=str, default='日本語')
parser.add_argument('--vanilla-modules', nargs='*', default=None, help='to specify vanilla module names. You can specify other modules if the official translation is BAD. NOTE: this function will work only if the modules contain both English and the target language files')
parser.add_argument(
    '--vanilla-merge-on', default='string', type=str,
    help="`none`, `string`, `id`, or `both`. how to merge with vanilla translation files. The default is `string`. The latter two values are NOT RECOMMENDED.  NOTE: the same ID means this text can't show because the localzation engine's failre"
    )
parser.add_argument(
    '--drop-original-language', default=False, action='store_true', help='suppress to merge the own language folder')
parser.add_argument(
    '--pofile', type=Path, default=None,
    help='additional translation file. PO or MO file are available. It requires the same format as what this script outputs') # TODO: 複数のファイルを参照 
# parser.add_argument('--distinct', default=False, action='store_true', help='drop duplicated IDs the last loaded entries are left per ID')
parser.add_argument('--fill-english', default=False, action='store_true', help='to fill the translated text with original (English) text')
parser.add_argument('--mb2dir', type=Path, default=None, help='MB2 install folder')
parser.add_argument('--autoid-prefix', type=str, default=None)
parser.add_argument('--keep-vanilla-id', default=False, action='store_true',
                    help='ignore vanilla IDs which has potential problems by reusing or abusing in the mod.')
# parser.add_argument('--keep-redundancies', default=False, action='store_true', help='whether or not add different IDs to entries with same strings')
parser.add_argument('--convert-exclam', default=False, action='store_true')
parser.add_argument('--verbose', default=False, action='store_true')
parser.add_argument('--dont-clean', default=False, action='store_true')
# parser.add_argument('--dont-complete-id', default=False, action='store_true', help="used for the REALISTIC BATTLE MOD")
parser.add_argument('--how-distinct', type=str, default='context', help='one of `context`, `file`, `all`')

FILTERS  = [
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

if __name__ == '__main__':
    args = parser.parse_args()
    with (Path('tools') if '__file__' in locals() else Path(__file__).parent).joinpath('default.yml') as fp:
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
    main()

# TODO: REFACTORING!!!

# TODO: たまに UTF-16で保存してくるやつがいる...
# TODO: 元テキスト変えてるやつも多いのでIDで紐づけはデフォでやらないように
# TODO: Mod作者はまずIDをまともに与えてないという想定で作る
# TODO: =! は何か特別な意味がある?
# TODO: 長い文のマッチングに失敗している?


def read_mod_languages(target_language:str, language_folder:Path)->pd.DataFrame:
    """
    Extract Text from all XML files in target module's ModuleData/Languages
    the target files must be listed in language_data.xml. Some mods failed to add this file even if this is an essential file.
    Moreover, English language file often contains irregular syntaces because of senseless engine implementation.
    """
    ds = []
    print(f'reading xml files from {language_folder}')
    language_files = []
    for lang_data_file in language_folder.rglob('./language_data.xml'):
        with lang_data_file.open('r', encoding='utf-8') as f:
            xml = BeautifulSoup(f, features='lxml-xml')
        xml_lang_data = xml.find('LanguageData')
        if xml_lang_data['id'] == target_language:
            language_files += [language_folder.joinpath(x['xml_path']) for x in xml_lang_data.find_all('LanguageFile')]
    for file in language_files:
        print(f'{target_language} language file: {file.relative_to(language_folder)}')
        d = langauge_xml_to_pddf(file, 'text', language_folder)
        if d.shape[0] > 0:
            ds += [d]
    if len(ds) > 0:
        data = pd.concat(ds)
        n = data.shape[0]
        data = data.groupby('id').first().reset_index()
        warnings.warn(f'''{n - data.shape[0]} duplicated ID found in the languag file!''')
    else:
        data = pd.DataFrame(columns=['id', 'text'])
    return data


def extract_all_text_from_xml(
        module_data_dir:Path,
        target_module:str,
        verbose:bool,
    )->pd.DataFrame:
    """
    # タグはいろいろあるので翻訳対象の条件づけが正確なのかまだ自信がない
    # TODO: ! とか * とか訳のわからんIDを付けているケースが多い. 何の意味が?
    """
    ds = []
    print(f'reading xml files from {module_data_dir}')
    for file in module_data_dir.rglob('./*.xml'):
        if file.relative_to(module_data_dir).parts[0].lower() != 'languages':            
            d = non_language_xml_to_pddf(file, file.relative_to(module_data_dir), verbose)
            print(f"""(not language file) {d.shape[0]} entries found in {file.relative_to(module_data_dir)}.""")
            ds += [d]
    for file in module_data_dir.glob('languages/*.xml'):
        d = langauge_xml_to_pddf(file, 'text_EN', module_data_dir)
        print(f"""(English language file) {d.shape[0]} entries found in {file.relative_to(module_data_dir)}.""")
        if d.shape[0] > 0:
            ds += [d]
    for file in module_data_dir.glob('languages/en/*.xml'):
        print(f"""(English language file) {d.shape[0]} entries found in {file.relative_to(module_data_dir)}.""")
        d = langauge_xml_to_pddf(file, 'text_EN', module_data_dir)
        if d.shape[0] > 0:
            ds += [d]
    for file in module_data_dir.glob('languages/English/*.xml'):
        print(f"""(English language file) {d.shape[0]} entries found in {file.relative_to(module_data_dir)}.""")
        d = langauge_xml_to_pddf(file, 'text_EN', module_data_dir)
        if d.shape[0] > 0:
            ds += [d]
    if len(ds) == 0:
        d_return = None
    else:
        d_return = pd.concat(ds)
        d_return = d_return.assign(
            text_EN=lambda d: np.where(d['text_EN'] == '', np.nan, d['text_EN'])
        )
    return d_return


def non_language_xml_to_pddf(fp:Path, base_dir:Path=fp.parent, verbose:bool=False)->pd.DataFrame:
    with base_dir.joinpath(fp).open('r', encoding='utf-8') as f:
        xml = BeautifulSoup(f, features='lxml-xml')
    ds = []
    for filter in FILTERS:
        xml_entries = xml.find_all(name=filter['name'], attrs={filter['attrs']: True})
        if verbose:
            print(f'''{len(xml_entries)} {filter['attrs']} attributes found in {filter['name']} tags''')
        if len(xml_entries) > 0:
            tmp = pd.DataFrame(
                [(x[filter['attrs']], f'''{filter['name']}.{filter['attrs']}''') for x in xml_entries],
                columns=['text_EN', 'context']
            ).assign(
                id = lambda d: np.where(
                    d['text_EN'].str.contains(r'^\{=(.+?)\}.*$', regex=True),
                    d['text_EN'].str.replace(r'^\{=(.+?)\}.*$', r'\1', regex=True),
                    ''
                ),
                file = fp,
                text_EN = lambda d: d['text_EN'].str.replace(r'^\{=.+?\}(.*)$', r'\1', regex=True),
                attr = filter['attrs']
            )
            ds += [tmp]
    if len(ds) > 0:
        return pd.concat(ds)
    else:
        return pd.DataFrame(columns=['id', 'text_EN', 'context', 'file', 'attr'])


def langauge_xml_to_pddf(fp:Path, text_col_name:str, base_dir:Path=fp.parent)->pd.DataFrame:
    with base_dir.joinpath(fp).open('r', encoding='utf-8') as f:
        xml = BeautifulSoup(f, features='lxml-xml')
    xml_entries = xml.find_all(name='string', attrs={'id': True, 'text': True})
    if len(xml_entries) > 0:
        d = pd.DataFrame(
            [(x['id'], x['text'], 'language.text') for x in xml_entries], columns=['id', text_col_name, 'context']
        ).assign(attr = 'string', file = fp.relative_to(base_dir))
        return d
    else:
        return pd.DataFrame(columns=['id', text_col_name, 'context', 'attr', 'file'])


def normalize_string_ids(
        data:pd.DataFrame,
        how_distinct:str,
        keep_redundancies:bool,
        keep_vanilla_id:bool,
        langshort:str,
        convert_exclam:bool,
        autoid_prefix:str)->pd.DataFrame:
    """
    後2つ以外のXML, module_string, language の順で信頼できるはずなので被ったらその優先順位でなんとかする.
    """
    vanilla_id_path = (Path('tools') if '__file__' not in locals() else Path(__file__).parent).joinpath('vanilla-id.csv')
    if not vanilla_id_path.exists():
        print(f'{vanilla_id_path} not found. trying to create vanilla-id.csv...')
        with Path(f'text/MB2BL-{langshort}.po') as fp:
            if fp.exists():
                export_id_text_list(fp, vanilla_id_path)
            else:
                warnings.warn(f'''{fp} not found. this process is skipped, but it will caused some ID detection errors.''')
                vanilla_ids = pd.DataFrame(columns=['id', 'text_EN'])
    if vanilla_id_path.exists():
        vanilla_ids = pd.read_csv(vanilla_id_path).assign(id_used_in_vanilla=True)
    lambda_id = (
        lambda d: np.where(
            (d['id'] == '') | d['id'].isna(),
            [f'{autoid_prefix}' + hashlib.sha256((text + str(i)).encode()).hexdigest()[-5:] for i, text in enumerate(d['context'] + d['attr'] + d['text_EN'])],  # TODO
            d['id']
        )
    ) if keep_redundancies else (
        lambda d: np.where(
            (d['id'] == '') | d['id'].isna(),
            [f'{autoid_prefix}' + hashlib.sha256(text.encode()).hexdigest()[-5:] for text in d['context'] + d['attr'] + d['text_EN']],  # TODO
            d['id']
        )
    )
    if not convert_exclam: 
        # TODO: なぜ!を付ける人が多いのか? このオプションいるか?
        # TODO: 翻訳が必要ないのは動的に名前が上書きされるテンプレートNPCの名称のみだが, それとは関係なく =! とか =* とか書いている人が多い. なんか独自ルールの記号使ってる人までいる…
        data = data.loc[lambda df: df['id'] != '!']
        # TODO: precise id detetion
        # TODO: IDに使用できる文字
        # TODO: テンプレートの名前かどうかを確実に判別する方法がない
    if not keep_vanilla_id:
        # テキストを変更しているのにバニラのIDを使いまわしている, あるいは偶然に被っている場合はIDを削除する
        # erase entry if both ID and the original string is the same. 
        data = data.merge(
            vanilla_ids.rename(columns={'text_EN': 'text_EN_original'}),
            on='id', how='left')
        data = data.assign(
            id = lambda d: np.where(d['id_used_in_vanilla'] & (d['text_EN'] != d['text_EN_original']), '', d['id'])
        )
        data = data.loc[lambda d: ~(d['id_used_in_vanilla'] & (d['text_EN'] == d['text_EN_original']))]
        data = data.drop(columns=['text_EN_original', 'id_used_in_vanilla'])
        # TODO: 常にバニラと比較するように
    data = data.assign(missing_id = lambda d: (d['id'].str.contains('^[?!\*]$')) | (d['id'] == '') | (d['id'] == '*'))
    if how_distinct == 'context':
        n = data.shape[0]
        data = data.groupby(['text_EN', 'context', 'attr']).agg({'id': lambda s: s.sort_values().iloc[0]}).reset_index()
        print(f'''{n - data.shape[0]} ID errors detected after making distinct by context and attr''')
    elif how_distinct == 'file':
        n = data.shape[0]
        data = data.groupby(['text_EN', 'context', 'attr', 'file']).agg({'id': lambda s: s.sort_values().iloc[0]}).reset_index()
        print(f'''{n - data.shape[0]} ID errors detected after making distinct by context and files''')
    else:
        errors = data.loc[lambda d: (d['id'] == '') | d['id'].isna()].shape[0]
        print(f'''{errors} ID errors detected after making distinct by context and files''')
    data = data.assign(id=lambda_id)
    return data


def merge_language_file(
        data:pd.DataFrame,
        data_language:pd.DataFrame=None,
        data_language_vanilla:pd.DataFrame=None,
        data_po:pd.DataFrame=None,
        translation_merge_on:str='both'
        )->pd.DataFrame:
    """
    each data frame must have unique id
    """
    if data_language is not None and data_language.shape[0] > 0:
        data = data.merge(data_language[['id', 'text']], on=['id'], how='left')
        n_missing = data.loc[lambda d: d['text'].isna()].shape[0]
        print(f'''{n_missing} IDs are not found''')
    else:
        data['text'] = np.nan
    if data_language_vanilla is not None and data_language_vanilla.shape[0] > 0:
        data = data.merge(data_language_vanilla[['id', 'text']], on=['id'], how='left')
        data = data.assign(text = lambda d: np.where(d['text'].isna(), d['text_y'], d['text_x'])).drop(columns=['text_x', 'text_y'])
    if data_po is not None and data_po.shape[0] > 0:
        if translation_merge_on in ['id', 'both']:
            data = data.merge(data_po[['id', 'text']], on=['id'], how='left')
            data = data.assign(text = lambda d: np.where(d['text'].isna(), d['text_y'], d['text_x'])).drop(columns=['text_x', 'text_y'])
        if translation_merge_on in ['string', 'both']:
            data = data.merge(data_po[['text_EN' 'text']], on=['text_EN'], how='left')
            data = data.assign(text = lambda d: np.where(d['text'].isna(), d['text_y'], d['text_x'])).drop(columns=['text_x', 'text_y'])
    return data


def export_corrected_xml_id(data:pd.DataFrame, module_data_dir:Path, dont_clean:bool, outdir:Path, target_module:str)->None:
    """
    read and correct wrong IDs in XMLs, and export them
    """
    for file in module_data_dir.rglob('./*.xml'):
        if file.relative_to(module_data_dir).parts[0].lower() != 'languages':            
            print(f"""(not language file) {file.relative_to(module_data_dir)}""")
            with file.open('r', encoding='utf-8') as f:
                xml = BeautifulSoup(f, features='lxml-xml')
            any_changes = False
            for filter in FILTERS:
                xml_entries = xml.find_all(name=filter['name'], attrs={filter['attrs']: True})
                d_sub =  data.loc[lambda d: (d['context'] == f"""{filter['name']}.{filter['attrs']}""") | (d['context'].isin(['module.string', 'text.string']))]
                for entry in xml_entries:
                    r = d_sub.loc[lambda d: (d['text_EN']) & (d['text'] != '')]
                    if r.shape[0] > 0:
                        new_string = '{=' + d_sub['id'][0] + '}' + d_sub['text_EN'][0]
                        if entry[filter['attrs']] != new_string:
                            entry[filter['attrs']] = new_string
                            any_change = True
        if any_changes:
            print(f'{file.name} is needed to be overwritten')
            outfp = outdir.joinpath(f'{target_module}/ModuleData/{file.relative_to(module_data_dir)}')
            if not dont_clean and outfp.exists():
                print(f'deleting output old {outfp.name}')
                outfp.unlink()
            with outfp.open('w', encoding='utf-8') as f:
                    f.writelines(xml.prettify(formatter='minimal'))
        any_changes = False


def pofile_to_df(pofile:Path)->pd.DataFrame:
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
        return po2pddf(catalog)
    else:
        warnings.warn(f'''{args.pofile} not found''')
        return None


def main():
    module_data_dir = args.mb2dir.joinpath(f'Modules/{args.target_module}/ModuleData')
    if not module_data_dir.exists():
        raise(f'''{module_data_dir} not found!''')
    d_mod = extract_all_text_from_xml(module_data_dir, args.target_module, args.verbose)
    n = d_mod.shape[0]
    print(f'''---- {n} entries detected from this mod ----''')
    d_mod = normalize_string_ids(d_mod, args.how_distinct, args.keep_redundancies, args.keep_vanilla_id, args.langshort, args.convert_exclam, args.autoid_prefix)
    print(f'''---- {n - d_mod.shape[0]} ID errors detected! ----''')
    print("---- Extract strings from ModuleData/Lanugages ----")
    d_mod_lang = read_mod_languages(args.langid, module_data_dir.joinpath('Languages'))
    d_po = pofile_to_df(args.pofile)

    d_mod = merge_language_file(d_mod, d_mod_lang, None, d_po, )
    export_corrected_xml_id(d_mod, module_data_dir)


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
