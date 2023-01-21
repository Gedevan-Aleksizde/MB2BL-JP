#! /usr/bin/env python3
# encoding: utf-8
import argparse
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
from babel import Locale # Babel
from babel.messages.pofile import read_po
from babel.messages.mofile import read_mo
from babel.messages.catalog import Catalog
import html

pofile = Path('text/translation-JP-pub.po')
output = Path('Modules')
mb2dir = Path('C:\Program Files (x86)\Steam\steamapps\common\Mount & Blade II Bannerlord')

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
parser.add_argument('--mb2dir', type=str, default=mb2dir)
parser.add_argument('--modules', nargs='*', default=modules)
parser.add_argument('--langfolder', type=str, default='JP')
parser.add_argument('--langsuffix', type=str, default='jpn')  
parser.add_argument('--functions', type=str, default='jp_functions.xml')  # why so diverse country codes used?? 
parser.add_argument('--langid', type=str, default='日本語') 
parser.add_argument('--langalias', type=str, default='正しい日本語')
parser.add_argument('--langname', type=str, default='日本語')
parser.add_argument('--subtitleext', type=str, default='jp')
parser.add_argument('--iso', type=str, default='ja,jpn,ja-ja,ja-jp,jp-jp') 
parser.add_argument('--output-type', type=str, default='both')

if __name__ == '__main__':
    args = parser.parse_args()

# TODO: highly doubtful localization modding system
# TODO: 挙動が非常に不可解. 重複を削除するとかえって動かなくなる. language_data 単位でsanity checkがなされている?
# <language>/<Module Names>/<xml> のように module 毎にフォルダを分け, それぞれに language_data.xml を用意すると動くことを発見. 不具合時の原因切り分けも多少しやすくなる
# TODO: 特殊な制御文字が結構含まれているわりにエンティティ化が必要かどうかが曖昧

def export(args, type):
    """
    type: 'module' or 'overwriter'
    """
    print(f'output type: {type}')
    if args.input.exists():
        with args.input.open('br') as f:
            if args.input.suffix == '.po':
                catalog = read_po(f)
            elif args.input.suffix == '.mo':
                catalog = read_mo(f)
            else:
                print('WARNING: input file is invalid')
    else:
        with args.input.parent.joinpath(f'translation-{args.langfolder}.po') as fp:
            if fp.exists():
                catalog = read_po(fp.open('br'))
    # TODO: why the iterator includes header lines
    d = pd.DataFrame(
        [(x.id, x.string) for x in catalog if x.id != ''], columns=['id', 'text']
        )
    d = pd.concat([d, d['id'].str.split('/', expand=True)], axis=1).drop(
        columns='id'
        ).rename(
            columns={0: 'module', 1: 'file', 2: 'id'}
            )
    d = d.assign(
        priority=lambda d: [args.modules.index(x) if x in args.modules else -1 for x in d['module']]
        ).sort_values(['id', 'module'], ascending=False).groupby(['id']).first().reset_index()
    d['text'] = d['text'].str.replace('%%', '%')
    d['id'] = d['id'].str.replace('%%', '%')
    n_entries_total = 0
    n_change_total = 0
    for module in args.modules:
        if type == 'module':
            output_dir = args.output.joinpath(f'CL{args.langfolder}-Common/ModuleData/Languages/{args.langfolder}').joinpath(module)
        elif type == 'overwriter':
            output_dir = args.output.joinpath(f'{module}/ModuleData/Languages/{args.langfolder}')
        # output_dir = args.output.joinpath(f'{module}/ModuleData/Languages/{args.langfolder}')
        xml_list = list(args.mb2dir.joinpath(f'''Modules/{module}/ModuleData/languages/{args.langfolder}''').glob('*.xml'))
        if len(xml_list) > 0:
            if not output_dir.exists() and len(xml_list) > 0:
                output_dir.mkdir(parents=True)
            n_entries_xml = 0
            n_change_xml = 0
            language_data = BeautifulSoup(
                f'''
                <LanguageData>
                </LanguageData>
                ''',
                'lxml-xml'
                )
            language_data.LanguageData['id'] = f'''correct_{args.langalias}''' if type == 'module' else args.langid
            if module == 'Native':
                language_data.LanguageData['name'] = f'''{args.langalias}''' if type == 'module' else args.langname
                if args.subtitleext != '':
                    language_data.LanguageData['subtitle_extension'] = args.subtitleext
                if args.iso != '':
                    language_data.LanguageData['supported_iso'] = args.iso
                language_data.LanguageData['under_development'] = 'false'
            for xml_path in xml_list:
                print(f'''Reading {xml_path.name} from {xml_path.parent.parent.parent.parent.name} Module''')
                # edit language_data.xml
                xml = BeautifulSoup(xml_path.open('r', encoding='utf-8'), features='lxml-xml')
                en_xml_name = pd.Series(xml_path.with_suffix('').name).str.replace(f'''-{args.langsuffix}''', '')[0] + '.xml'
                d_sub = d.loc[lambda d: (d['module'] == module) & (d['file'] == en_xml_name)]
                if xml.find('base', recursive=False) is not None:
                    if type == 'module':
                        xml.base.find('tags', recursive=False).append(BeautifulSoup(f'''<tag language="correct_{args.langalias}" />''', features='lxml-xml'))
                    if xml.base.find('strings', recursive=False) is not None:
                        for string in xml.base.find('strings', recursive=False).find_all('string', recursive=False):
                            tmp = d_sub.loc[lambda d: d['id'] == string['id'], ]['text'].values
                            if tmp.shape[0] > 0 and tmp[0] != '' and string['text'] != tmp[0]:
                                string['text'] =  html.escape(tmp[0])
                                n_change_xml += 1
                            n_entries_xml += 1
                        if n_entries_xml > 0:
                            print(f'''{100 * n_change_xml/n_entries_xml:.0f} % out of {n_entries_xml} text are changed in {xml_path.name}''')
                        else:
                            print(f'''no translation entries in {xml_path.name}''')
                    n_entries_total += n_entries_xml
                    n_change_total += n_change_xml
                    language_data.LanguageData.append(
                        BeautifulSoup(
                            f'''<LanguageFile xml_path="{Path('/'.join([args.langfolder, module if type == 'module' else '', xml_path.name])).as_posix()}" />''',
                            features='lxml-xml'
                            )
                            )
                    output_dir.joinpath(f'''{xml_path.name}''').open('w', encoding='utf-8').writelines(xml.prettify(formatter='minimal'))
            output_dir.joinpath('language_data.xml').open('w', encoding='utf-8').writelines(language_data.prettify())
    if n_entries_total > 0:
        print(f'''{100 * n_change_total/n_entries_total:.0f} % out of {n_entries_total} text are changed totally''')

if args.output_type == 'both':
    for x in ['module', 'overwriter']:
        export(args, x)
elif args.output_type == 'module':
    export(args, 'module')
elif args.output_type == 'overwriter':
    export(args, 'overwriter')
else:
    print(f'WARNING: {args.output_type} must be "module", "overwriter", or "both" ')