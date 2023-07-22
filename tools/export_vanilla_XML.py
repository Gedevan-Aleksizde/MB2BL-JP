#! /usr/bin/env python3
# encoding: utf-8
import argparse
import yaml
from pathlib import Path
import warnings

from bs4 import BeautifulSoup
import pandas as pd
from babel import Locale # Babel
from babel.messages.pofile import read_po, write_po
from babel.messages.mofile import read_mo, write_mo
from babel.messages.catalog import Catalog
import regex
from functions import po2pddf, removeannoyingchars, public_po, get_catalog_which_has_corrected_babel_fake_id, merge_yml

pofile = Path('text/MB2BL-Jp.po')
output = Path('Modules')

modules = [
    'DedicatedCustomServerHelper',
    'SandBoxCore',
    'SandBox',
    'MultiPlayer',
    'CustomBattle',
    'StoryMode',
    'BirthAndDeath',
    'Native',
    ]

parser = argparse.ArgumentParser()
parser.add_argument("--input", type=Path, default=pofile)
parser.add_argument("--output", type=Path, default=output)
parser.add_argument('--mb2dir', type=str, default=None)
parser.add_argument('--modules', nargs='*', default=modules)
parser.add_argument('--langshort', type=str, default=None)
parser.add_argument('--langsuffix', type=str, default='jpn') 
parser.add_argument('--functions', type=str, default='jp_functions.xml')  # why so diverse country codes used?? 
parser.add_argument('--langid', type=str, default=None)
parser.add_argument('--langalias', type=str, default=None)
# parser.add_argument('--langname', type=str, default='日本語')
parser.add_argument('--subtitleext', type=str, default='jp')
parser.add_argument('--iso', type=str, default=None)
parser.add_argument('--output-type', type=str, default='module')
parser.add_argument('--with-id', default=None, action='store_true')
parser.add_argument('--distinct', default=None, action='store_true', help='drop duplicated IDs in non-Native modules')
parser.add_argument('--no-english-overwriting', default=None, action='store_true', help='for M&B weird bug')
parser.add_argument('--legacy_id', action='store_true', help='depricated')
parser.add_argument('--suppress-missing-id', default=False, action='store_true')
parser.add_argument('--dont-clean', default=False, action='store_true')
parser.add_argument('--missing-modulewise', default=False, action='store_true')


def main():
    args = parser.parse_args()
    with Path(__file__).parent.joinpath('default.yml') as fp:
        if fp.exists():
            with Path(__file__).parent.joinpath('default.yml') as fp:
                args = merge_yml(fp, args, parser.parse_args([]))
    print(args)
    if args.output_type == 'both':
        for x in ['module', 'overwriter']:
            export_modules(args, x)
    elif args.output_type == 'module':
        export_modules(args, 'module')
    elif args.output_type == 'overwriter':
        export_modules(args, 'overwriter')
    else:
        warnings.warn(f'{args.output_type} must be "module", "overwriter", or "both" ', UserWarning)


# TODO: 挙動が非常に不可解. 重複を削除するとかえって動かなくなる? language_data 単位でsanity checkがなされている?
# <language>/<Module Names>/<xml> のように module 毎にフォルダを分け, それぞれに language_data.xml を用意すると動くことを発見. 不具合時の原因切り分けも多少しやすくなる
# 仕様が変なだけでなく厄介なバグもいくつかありそう
# TODO: 特殊な制御文字が結構含まれているわりにエンティティ化が必要かどうかが曖昧
# NOTE: quoteation symbols don't need to be escaped (&quot;) if quoted by another ones
# TODO: too intricate to localize

def export_modules(args, type):
    """
    type: 'module' or 'overwriter'
    """
    print(f'output type: {type}')
    if args.input.exists():
        with args.input.open('br') as f:
            if args.input.suffix == '.po':
                print(f'reading {args.input}')
                catalog = read_po(f)
            elif args.input.suffix == '.mo':
                print(f'reading {args.input}')
                catalog = read_mo(f)
            else:
                raise('input file is invalid', UserWarning)
    catalog = get_catalog_which_has_corrected_babel_fake_id(catalog)
    catalog_pub = public_po(catalog)
    with args.input.parent.joinpath(args.input.with_suffix('').name + '-pub.po').open('bw') as f:
        write_po(f, catalog_pub)
    with args.input.parent.joinpath(args.input.with_suffix('').name + '-pub.mo').open('bw') as f:
        write_mo(f, catalog_pub)
    del catalog_pub
    d = po2pddf(catalog, drop_prefix_id=False)
    if not args.legacy_id:
        d = pd.concat(
            [
                d,
                d['context'].str.split('/', expand=True).rename(columns={0: 'module', 1: 'file'})
            ],
            axis=1
        )[['id', 'text', 'text_EN', 'module', 'file', 'locations']]
        d['duplication'] = [len(x) for x in d['locations']]
        d['duplication'] = d['duplication'].fillna(1)
    del catalog

    if args.distinct:
        n = d.shape[0]
        d = d.assign(
            isnative=lambda d: d['module'] == 'Native'
        ).sort_values(
            ['id', 'isnative']
        ).groupby(['id']).last().reset_index().drop(columns=['isnative'])
        print(f"""{n - d.shape[0]} duplicated entries dropped""")
    if 'duplication' not in d.columns:
        d['duplication'] = 1
    n_entries_total = 0
    n_change_total = 0
    for module in args.modules:
        if type == 'module':
            output_dir = args.output.joinpath(f'CL{args.langshort}-Common/ModuleData/Languages/{args.langshort}').joinpath(module)
        elif type == 'overwriter':
            output_dir = args.output.joinpath(f'{module}/ModuleData/Languages/{args.langshort}')
        if not output_dir.exists():
            output_dir.mkdir(parents=True)        
        xml_list = list(args.mb2dir.joinpath(f'''Modules/{module}/ModuleData/languages/{args.langshort}''').glob('*.xml'))
        if len(xml_list) > 0:
            if not output_dir.exists() and len(xml_list) > 0:
                output_dir.mkdir(parents=True)
            n_entries_xml = 0
            n_change_xml = 0
            language_data = generate_language_data_xml(module, id=args.langid, subtitle=args.subtitleext, iso=args.iso)
            for xml_path in xml_list:
                print(f'''Reading {xml_path.name} from {xml_path.parent.parent.parent.parent.name} Module''')
                # edit language_data.xml
                with xml_path.open('r', encoding='utf-8') as f:
                    xml = BeautifulSoup(f, features='lxml-xml')
                en_xml_name = pd.Series(xml_path.with_suffix('').name).str.replace(f'''_{args.langsuffix}''', '')[0] + '.xml'
                #TODO: refactoring
                if args.legacy_id:
                    d_sub = d.loc[lambda d: (d['module'] == module) & (d['file'] == en_xml_name)]
                else:
                    if not args.missing_modulewise:
                        d_sub = d.loc[lambda d: d['file'] == en_xml_name]
                    else:
                        d_sub = d
                    # TODO: language files get messed since v1.2.
                    # ファイルごとに分けることが無意味になった. IDさえ一意ならいいので元のファイルの分け方を守る必要もなさそう
                if xml.find('base', recursive=False) is not None:
                    default_lang_tag = xml.base.find('tag').get('language')
                    if default_lang_tag != args.langid:
                        xml.base.find('tags', recursive=False).append(generate_tag(args.langid))
                    if args.langalias is not None:
                        xml.base.find('tags', recursive=False).append(generate_tag(f'correct_{args.langidalias}'))
                    if xml.base.find('strings', recursive=False) is not None:
                        for string in xml.base.find('strings', recursive=False).find_all('string', recursive=False):
                            tmp = d_sub.loc[lambda d: d['id'] == string['id']]
                            if tmp.shape[0] > 0 and tmp['text'].values[0] != '':
                                new_str = removeannoyingchars(tmp['text'].values[0])
                                if string['text'] != new_str:
                                    string['text'] = new_str
                                    n_change_xml += 1
                                if not args.missing_modulewise:
                                    d = d.loc[lambda d: d['id'] != string['id']]
                            else:
                                if args.legacy_id:
                                    warnings.warn(f'''ID not found: {string["id"]} in {module}/{xml_path.name}''')
                                elif not d.loc[lambda d: d['id'] == string['id']].shape[0] > 0:
                                    warnings.warn(f'''ID not found: {string["id"]} in {module}/{xml_path.name}''')
                                normalized_str = removeannoyingchars(string['text'])
                                if normalized_str != string['text']:
                                    warnings.warn(
                                        f'''this text could contain irregular characters (some control characters or zenkaku blanks): {string['text']}''',
                                        UserWarning)
                                    n_change_xml += 1
                                    string['text'] = normalized_str
                                if args.distinct:
                                    string.extract()
                            n_entries_xml += 1
                            if args.with_id:
                                string['text'] = f"""[{string['id']}]{string['text']}"""
                        if n_entries_xml > 0:
                            print(f'''{100 * n_change_xml/n_entries_xml:.0f} % out of {n_entries_xml} text are changed in {xml_path.name}''')
                        else:
                            print(f'''no translation entries in {xml_path.name}''')
                    n_entries_total += n_entries_xml
                    n_change_total += n_change_xml
                    language_data.LanguageData.append(
                        generate_languageFile(
                        f"{Path('/'.join([args.langshort, module if type == 'module' else '', xml_path.name])).as_posix()}"
                        )
                        )
                    output_dir.joinpath(f'''{xml_path.name}''').open('w', encoding='utf-8').writelines(xml.prettify(formatter='minimal'))
            output_dir.joinpath('language_data.xml').open('w', encoding='utf-8').writelines(language_data.prettify())
            if not args.suppress_missing_id and args.missing_modulewise:
                print(f'------ Checking missing IDs in {module} ---------')
                df_original = pd.read_excel('text/MB2BL-JP.xlsx')
                n_missings = output_missings_modulewise(args, output_dir, module, d.loc[lambda d: d['module'] == module], df_original)
                print(f'{n_missings} missing IDs found!')
                if n_missings is not None:
                    n_entries_total += n_missings
                    n_change_total += n_missings
    if type=='module' and not args.no_english_overwriting:
        lang_data_patch = generate_language_data_xml(module='', id='English')
        lang_data_patch.LanguageData.append(generate_languageFile(f'{args.langshort}/Native/std_global_strings_xml_{args.langsuffix}.xml'))
        with output_dir.joinpath('../../language_data.xml').open('w', encoding='utf-8') as f:
            f.writelines(lang_data_patch.prettify())
    if type == 'module' and args.langalias is not None:
        with args.output.joinpath(f'CL{args.langshort}-Common/ModuleData/Languages/{args.langshort}/Native/language_data.xml').open('r', encoding='utf-8') as f:
            language_data_alias = BeautifulSoup(f, features='lxml-xml')
        language_data = language_data_alias.find('LanguageData', recursive=False)
        language_data['id'] = f'correct_{args.langalias}'
        language_data['name'] = args.langalias
        xml_list = args.output.joinpath(f'CL{args.langshort}-Common/ModuleData/Languages/{args.langshort}').rglob('language_data.xml')
        for fp in xml_list:
            if fp.parent != 'Native':
                with fp.open('r', encoding='utf-8') as f:
                    langauage_data2 =  BeautifulSoup(f, features='lxml-xml')
                    for xml_languagefile in langauage_data2.find_all('LanguageFile'):
                        language_data_alias.find('LanguageData').append(xml_languagefile)
        output_fp = args.output.joinpath(f'CL{args.langshort}-Common/ModuleData/Languages/{args.langshort}2/language_data.xml')
        if not output_fp.parent.exists():
            output_fp.parent.mkdir(parents=True)
        with output_fp.open('w', encoding='utf-8') as f:
            f.writelines(language_data_alias.prettify())
    if n_entries_total > 0:
        print(f'''SUMMARY: {100 * n_change_total/n_entries_total:.0f} % out of {n_entries_total} text are changed totally''')
    if not args.suppress_missing_id and not args.missing_modulewise and d.shape[0] > 0:
        print(f'------ Checking missing IDs whole the vanilla text ---------')
        output_dir = args.output.joinpath(f'CL{args.langshort}-Common/ModuleData/Languages/{args.langshort}').joinpath('Missings')
        if not output_dir.exists():
            output_dir.mkdir()
        language_data_missings = generate_language_data_xml(module='', id=args.langid)
        language_data_missings.LanguageData.append(generate_languageFile(f'{args.langshort}/Missings/str_missings-{args.langsuffix}.xml'))
        language_data_missings.LanguageData.append(generate_languageFile(f'{args.langshort}/Missings/ str_sandbox_missings-{args.langsuffix}.xml'))
        output_dir.joinpath(f'''language_data.xml''').open('w', encoding='utf-8').writelines(language_data_missings.prettify(formatter='minimal'))
        xml_str_missings = generate_string_xml([args.langid])
        for i, r in d.iterrows():
            new_entry = generate_new_string(r['id'], removeannoyingchars(r['text']))
            xml_str_missings.base.find('strings').append(new_entry)
        print(f'''SUMMARY: {d.shape[0]} entries out of {n_entries_xml} ({100 * (d.shape[0]/n_entries_total):.0f}%) are missing from vanilla {args.langid} language files.''')
        output_dir.joinpath(f'''str_missings-{args.langsuffix}.xml''').open('w', encoding='utf-8').writelines(xml_str_missings.prettify(formatter='minimal'))
        print(f'''saved to {output_dir}''')


def output_missings_modulewise(args, output_dir, module, df, df_original=None):
    if df_original is not None:
        ids = df_original.loc[lambda d: (d['text_JP_original'] == '') | d['text_JP_original'].isna()][['id']]
        d_sub = df.merge(ids, on='id', how='inner')
    elif 'is_missing' in df.columns:
        d_sub = df.loc[lambda d: d['id_missing']]
    else:
        return None
    if d_sub.shape[0] < 1:
        return None
    xml = generate_string_xml([args.langid])
    strings = xml.base.find('strings', recursive=False)
    for i, r in d_sub.iterrows():
        strings.append(generate_new_string(r['id'], removeannoyingchars(r['text'])))
    with output_dir.joinpath(f'translation-missings-{args.langshort}.xml').open('w', encoding='utf-8') as f:
        f.writelines(xml.prettify(formatter='minimal'))
    with output_dir.joinpath(f'language_data.xml').open('r', encoding='utf-8') as f:
        xml_lang_data = BeautifulSoup(f.read(), 'lxml-xml')
    lang_data_xml = xml_lang_data.find('LanguageData')
    new_entry = generate_languageFile(path=f'{args.langshort}/{module}/translation-missings-{args.langshort}.xml')
    lang_data_xml.append(new_entry)
    with output_dir.joinpath(f'language_data.xml').open('w', encoding='utf-8') as f:
        f.writelines(lang_data_xml.prettify(formatter='minimal'))
    return d_sub.shape[0]


def generate_language_data_xml(module:str, id:str, name:str=None, subtitle:str=None, iso:str=None, dev:str='false') -> BeautifulSoup: 
    language_data = BeautifulSoup(
    f'''
    <LanguageData>
    </LanguageData>
    ''', features='lxml-xml'
    )
    language_data.LanguageData['id'] = id
    if module == 'Native':
        language_data.LanguageData['name'] = id if name is None else name
    if subtitle is not None:
        language_data.LanguageData['subtitle_extension'] = subtitle
    if iso is not None:
        language_data.LanguageData['supported_iso'] = iso
    language_data.LanguageData['under_development'] = dev
    return language_data


def generate_string_xml(langids:list) -> BeautifulSoup:
    xml = BeautifulSoup(
        f'''
        <base>
        <tags></tags>
        <strings></strings>
        </base>
        ''', features='lxml-xml')
    [xml.base.tags.append(BeautifulSoup(f'<tags id="{id}" />', features='lxml-xml')) for id in langids]
    return xml


def generate_tag(langid:str) -> BeautifulSoup:
    return BeautifulSoup(f'<tag language={langid} />', features='lxml-xml')


def generate_languageFile(path:str) -> BeautifulSoup:
    return BeautifulSoup(f'<LanguageFile xml_path="{path}" />', features='lxml-xml')


def generate_new_string(id:str, text:str):
    new_entry = BeautifulSoup(f'''<string id="PLAHECOLHDER" text="[PLACEHOLDER]" />''', features='lxml-xml')
    new_entry.find('string')['id']= id
    new_entry.find('string')['text']= text
    return new_entry


if __name__ == '__main__':
    main()