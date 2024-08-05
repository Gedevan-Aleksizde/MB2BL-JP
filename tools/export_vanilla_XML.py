#! /usr/bin/env python3
# encoding: utf-8
import argparse
from pathlib import Path
import warnings
from typing import Optional

import lxml.etree as ET
import html
import pandas as pd
import polib
from functions import po2pddf, removeannoyingchars, public_po, merge_yml
from typing import Iterable, List, Tuple, Dict

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
parser.add_argument('--langfolder-output', type=str, default=None)
parser.add_argument('--langsuffix', type=str, default='jpn') 
parser.add_argument('--functions', type=str, default='jp_functions.xml')  # why so diverse country codes used?? 
parser.add_argument('--langid', type=str, default=None)
parser.add_argument('--langalias', type=str, default=None)
# parser.add_argument('--langname', type=str, default='日本語')
parser.add_argument('--subtitleext', type=str, default='jp')
parser.add_argument('--iso', type=str, default=None)
parser.add_argument('--output-type', type=str, default='module')
parser.add_argument('--with-id', default=None, action='store_true', help='append IDs to strings for debugging')
parser.add_argument('--all-entries', default=None, action='store_true', help='to output unchanged entries')
parser.add_argument('--skip-blank_vanilla', default=None, action='store_true', help='to suprress to output bkank entries')
parser.add_argument('--distinct', default=None, action='store_true', help='drop duplicated IDs in non-Native modules')
parser.add_argument('--no-english-overwriting', default=None, action='store_true', help='for M&B weird bug')
parser.add_argument('--legacy_id', action='store_true', help='depricated. for old version of this script')
parser.add_argument('--suppress-missing-id', default=False, action='store_true', help='to supress to output unmatched IDs')
parser.add_argument('--dont-clean', default=False, action='store_true', help='to keep old files in the output folder')
parser.add_argument('--missing-modulewise', default=False, action='store_true')
parser.add_argument('--filename-sep-version', default=None, type=str, help="`1.0`, `1.1` or `1.2`. Why the file names changed at random?")
parser.add_argument('--verbose', default=None, action='store_true', help='output verbose log')

def main():
    args = parser.parse_args()
    with Path(__file__).parent.joinpath('default.yml') as fp:
        if fp.exists():
            with Path(__file__).parent.joinpath('default.yml') as fp:
                args = merge_yml(fp, args, parser.parse_args([]))
    if args.langfolder_output is None:
        args.langfolder_output = args.langshort
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

def export_modules(args: argparse.Namespace, type:str):
    """
    type: 'module' or 'overwriter'
    """

    df_to_be_dropped = pd.read_csv(Path(__file__).parent.joinpath('duplications.csv'))

    print(f'output type: {type}')
    if args.input.exists():
        if args.input.suffix == '.po':
            print(f'reading {args.input}')
            pof = polib.pofile(args.input)
        elif args.input.suffix == '.mo':
            print(f'reading {args.input}')
            pof = polib.pofile(args.input)
        else:
                raise('input file is invalid', UserWarning)
    pof_pub = public_po(pof)
    pof_pub.save(args.input.parent.joinpath(args.input.with_suffix('').name + '-pub.po'))
    pof_pub.save_as_mofile(args.input.parent.joinpath(args.input.with_suffix('').name + '-pub.mo'))
    del pof_pub
    d = po2pddf(pof, drop_prefix_id=False)
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
    if args.skip_blank_vanilla:
        d = d.loc[lambda d: d['text'] != '']
    del pof

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
            output_dir = args.output.joinpath(
                f'CL{args.langshort}-Common/ModuleData/Languages/{args.langfolder_output}'
                ).joinpath(module)
        elif type == 'overwriter':
            output_dir = args.output.joinpath(
                f'{module}/ModuleData/Languages/{args.langfolder_output}'
                )
        if not output_dir.exists():
            output_dir.mkdir(parents=True)
        base_langauge_path = f'''Modules/{module}/ModuleData/languages/{args.langshort}'''
        xml_list: List[Path] = [x for x in args.mb2dir.joinpath(base_langauge_path).glob('*.xml') if x.name not in ['language_data.xml', f'{args.langshort.lower()}_functions.xml'] ]
        if len(xml_list) > 0:
            if not output_dir.exists() and len(xml_list) > 0:
                output_dir.mkdir(parents=True)
            n_entries_xml = 0
            n_change_xml = 0
            language_data = generate_language_data_xml(module, id=args.langid, subtitle=args.subtitleext, iso=args.iso)
            for xml_path in xml_list:
                print(f'''Reading {xml_path.name} from {xml_path.parent.parent.parent.parent.name} Module''')
                # edit language_data.xml
                xml = ET.parse(xml_path)
                en_xml_name = pd.Series(xml_path.with_suffix('').name).str.replace(f'''{args.filename_sep}{args.langsuffix}''', '')[0] + '.xml'
                #TODO: refactoring
                if args.legacy_id:
                    d_sub = d.loc[lambda d: (d['module'] == module) & (d['file'] == en_xml_name)]
                    if d_sub.shape[0] == 0:
                        warnings.warn(f'no match entries with {en_xml_name}! subsettings skipped, which cause a bit low performance.')
                        d_sub =  d.loc[lambda d: (d['module'] == module)]
                else:
                    if args.missing_modulewise:
                        d_sub = d
                    else:
                        d_sub = d.loc[lambda d: d['file'] == en_xml_name]
                        if d_sub.shape[0] == 0:
                            d_sub = d
                            warnings.warn(f'no match entries with {en_xml_name}! subsettings skipped, which cause a bit low performance.')
                    # TODO: language files get messed since v1.2.
                    # ファイルごとに分けることが無意味になった. IDさえ一意ならいいので元のファイルの分け方を守る必要もなさそう
                if xml.getroot().tag == 'base':
                    if xml.find('tags/tag').attrib['language'] != args.langid:
                        xml.xpath('tags').append(generate_tag_element(args.langid))
                    if args.langalias is not None:
                        xml.xpath('tags').append(generate_tag_element(args.langalias))
                    if xml.find('strings') is not None:
                        for string in xml.xpath('strings/string'):
                            tmp = d_sub.loc[lambda d: d['id'] == string.attrib['id']]
                            n_entries_xml += 1
                            if drop_new_duplication_error_manually(
                                string,
                                df_to_be_dropped.loc[
                                    lambda d: (d['module']==module) & (d['file']==xml_path.name)
                                ]['id'].values
                            ):
                                n_change_total += 1
                            elif tmp.shape[0] > 0 and tmp['text'].values[0] != '':
                                new_str = removeannoyingchars(tmp['text'].values[0])
                                if string.attrib['text'] != new_str or args.all_entries:
                                    string.attrib['text'] = new_str
                                    n_change_xml += 1
                                if not args.missing_modulewise:
                                    d = d.loc[lambda d: d['id'] != string.attrib['id']]
                            else:
                                if args.legacy_id:
                                    warnings.warn(f'''ID not found: {string.attrib["id"]} in {module}/{xml_path.name}''')
                                elif not d.loc[lambda d: d['id'] == string.attrib['id']].shape[0] > 0 and args.verbose:
                                    warnings.warn(f'''ID not found: {string.attrib["id"]} in {module}/{xml_path.name}''')
                                normalized_str = removeannoyingchars(string.attrib['text'])
                                if normalized_str != string.attrib['text']:
                                    warnings.warn(
                                        f'''this text could contain irregular characters (some control characters or zenkaku blanks): {string.attrib['text']}''',
                                        UserWarning)
                                    n_change_xml += 1
                                    string.attrib['text'] = normalized_str
                                if args.distinct:
                                    html.unescape((ET.tostring(string, encoding='unicode')))
                            if args.with_id:
                                string.attrib['text'] = f"""[{string.attrib['id']}]{string.attrib['text']}"""
                        if n_entries_xml > 0:
                            print(
                                f'''{n_change_xml}/{n_entries_xml} ({100 * n_change_xml/n_entries_xml:.0f} %) text entries are changed in {xml_path.name}'''
                                )
                        else:
                            print(f'''no translation entries in {xml_path.name}''')
                        n_entries_total += n_entries_xml
                        n_change_total += n_change_xml
                    else:
                        warnings.warn(f'{xml_path} is has no strings tag! processing skipped')
                    language_data.getroot().append(
                        generate_languageFile_element(f"{Path('/'.join([args.langfolder_output, module if type == 'module' else '', xml_path.name])).as_posix()}")
                        )
                    write_xml_with_default_setting(xml, output_dir.joinpath(f'''{xml_path.name}'''))
                else:
                        warnings.warn(f'{xml_path} has no base tag! processing skipped')
            write_xml_with_default_setting(language_data, output_dir.joinpath('language_data.xml'))
            if not args.suppress_missing_id and args.missing_modulewise:
                print(f'------ Checking missing IDs in {module} ---------')
                df_original = pd.read_excel('text/MB2BL-JP.xlsx')
                n_missings = output_missings_modulewise(args, output_dir, module, d.loc[lambda d: d['module'] == module], df_original)
                print(f'{n_missings} missing IDs found!')
                if n_missings is not None:
                    n_entries_total += n_missings
                    n_change_total += n_missings
        else:
            print(f'''No language files found inside {base_langauge_path}''')
    if type=='module' and not args.no_english_overwriting:
        lang_data_patch = generate_language_data_xml(module='', id='English')
        lang_data_patch.getroot().append(generate_languageFile_element(f'{args.langfolder_output}/Native/std_global_strings_xml_{args.langsuffix}.xml'))
        write_xml_with_default_setting(lang_data_patch, output_dir.joinpath('../../language_data.xml'))
    if type == 'module' and args.langalias is not None:
        with args.output.joinpath(f'CL{args.langshort}-Common/ModuleData/Languages/{args.langfolder_output}/Native/language_data.xml') as fp:
            language_data_alias = ET.parse(fp)
        language_data = language_data_alias.find('LanguageData', recursive=False)
        language_data.attrib['id'] = args.langalias
        language_data.attrib['name'] = args.langalias
        xml_list = args.output.joinpath(f'CL{args.langshort}-Common/ModuleData/Languages/{args.langfolder_output}').rglob('language_data.xml')
        for fp in xml_list:
            if fp.parent != 'Native':
                langauage_data2 =  ET.parse(fp)
                for xml_languagefile in langauage_data2.findall('LanguageFile'):
                    language_data_alias.getroot().append(xml_languagefile)
        output_fp = args.output.joinpath(f'CL{args.langshort}-Common/ModuleData/Languages/{args.langfolder_output}2/language_data.xml')
        if not output_fp.parent.exists():
            output_fp.parent.mkdir(parents=True)
        write_xml_with_default_setting(language_data_alias, output_fp)
    if n_entries_total > 0:
        print(f'''SUMMARY: {n_change_total}/{n_entries_total} ({100 * n_change_total/n_entries_total:.0f}%) text entries are changed totally''')
    if not args.suppress_missing_id and not args.missing_modulewise and d.shape[0] > 0:
        print(f'------ Checking missing IDs whole the vanilla text ---------')
        output_dir = args.output.joinpath(f'CL{args.langshort}-Common/ModuleData/Languages/{args.langfolder_output}').joinpath('Missings')
        if not output_dir.exists():
            output_dir.mkdir()
        language_data_missings = generate_language_data_xml(module='', id=args.langid)
        language_data_missings.getroot().append(generate_languageFile_element(f'{args.langfolder_output}/Missings/str_missings-{args.langsuffix}.xml'))
        language_data_missings.getroot().append(generate_languageFile_element(f'{args.langfolder_output}/Missings/str_sandbox_missings-{args.langsuffix}.xml'))
        write_xml_with_default_setting(language_data_missings, output_dir.joinpath(f'''language_data.xml'''))
        xml_str_missings = generate_string_xml([args.langid])
        for i, r in d.iterrows():
            new_entry = generate_new_string_element(r['id'], removeannoyingchars(r['text']))
            xml_str_missings.find('strings').append(new_entry)
        print(f'''SUMMARY: {d.shape[0]} entries out of {n_entries_xml} ({100 * (d.shape[0]/n_entries_total):.0f}%) are missing from vanilla {args.langid} language files.''')
        write_xml_with_default_setting(xml_str_missings, output_dir.joinpath(f'''str_missings-{args.langsuffix}.xml'''))
        print(f'''saved to {output_dir}''')


def output_missings_modulewise(args: argparse.Namespace, output_dir: Path, module: str, df: pd.DataFrame, df_original: Optional[pd.DataFrame]=None):
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
    strings = xml.findall('strings')
    for i, r in d_sub.iterrows():
        strings.append(generate_new_string_element(r['id'], removeannoyingchars(r['text'])))
    write_xml_with_default_setting(xml, output_dir.joinpath(f'translation-missings-{args.langshort}.xml'))
    with output_dir.joinpath(f'language_data.xml') as fp:
        xml_lang_data = ET.parse(fp)
    lang_data_xml = xml_lang_data.find('LanguageData')
    new_entry = generate_languageFile_element(
        path=f'{args.langshort}/{module}/translation-missings-{args.langfolder_output}.xml'
        )
    lang_data_xml.append(new_entry)
    lang_data_xml.write(
        output_dir.joinpath(f'language_data.xml'),
        pretty_print=True,
        xml_declaration=True,
        encoding='utf-8'
    )
    return d_sub.shape[0]


def drop_new_duplication_error_manually(string: ET._Element, id_list: Iterable[str]) -> bool:
    """
    Return: number of dropped entries
    """
    if string.attrib['id'] in id_list:
        id_ = string.attrib['id']
        string.getparent().remove(string)
        print(f'duplicated ID ({id_}) dropprd')
        return True
    else:
        return False


def generate_language_data_xml(module:str, id:str, name:Optional[str]=None, subtitle:Optional[str]=None, iso:Optional[str]=None, dev:str='false')->ET.ElementTree: 
    language_data = ET.fromstring(
    f'''
    <LanguageData>
    </LanguageData>
    '''
    )
    language_data.set('id',id)
    if module == 'Native':
        language_data.set('name', id if name is None else name)
    if subtitle is not None:
        language_data.set('subtitle_extension', subtitle)
    if iso is not None:
        language_data.set('supported_iso', iso)
    language_data.set('under_development', dev)
    return ET.ElementTree(language_data)


def generate_string_xml(langids:list)->ET.ElementTree:
    xml = ET.fromstring(
        f'''
        <base>
        <tags></tags>
        <strings></strings>
        </base>
        ''')
    [xml.find('tags').append(ET.fromstring(f'<tag id="{id}" />')) for id in langids]
    return ET.ElementTree(xml)


def generate_tag_element(langid:str)->ET.ElementTree:
    return ET.fromstring(f'<tag language="{langid}" />')


def generate_languageFile_element(path:str)->ET.ElementTree:
    return ET.fromstring(f'<LanguageFile xml_path="{path}" />')


def generate_new_string_element(id:str, text:str):
    new_entry = ET.fromstring(f'''<string id="PLAHECOLHDER" text="[PLACEHOLDER]" />''')
    new_entry.attrib['id']= id
    new_entry.attrib['text']= text
    return new_entry


def write_xml_with_default_setting(xml:ET.ElementTree, fpath:Path)->bool:
    ET.indent(xml, space="  ", level=0)
    xml.write(
       fpath,
       pretty_print=True,
       xml_declaration=True,
       encoding='utf-8'
    )
    return True

if __name__ == '__main__':
    main()