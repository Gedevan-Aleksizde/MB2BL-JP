#! /usr/bin/env python3

import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path
import regex
import argparse
import numpy as np
from functions import (
    read_xmls, check_duplication, escape_for_po,
    update_with_older_po,
    get_localization_entries, get_default_lang,
    po2pddf_easy, pddf2po
    )
from babel.messages.pofile import read_po, write_po

mb2dir = Path('C:\Program Files (x86)\Steam\steamapps\common\Mount & Blade II Bannerlord')
modules = [
    'SandBoxCore',
    'SandBox',
    'CustomBattle',
    'MultiPlayer',
    'StoryMode',
    'Native',
    'CorrectLocalizationJP-Text',
    'Dummy'
]


parser = argparse.ArgumentParser()
parser.add_argument('target_module', type=str)
parser.add_argument('--outdir', type=Path, default=None)
parser.add_argument('--modules', nargs='*', default=modules)
parser.add_argument('--langshort', type=str, default='JP')
parser.add_argument('--langid', type=str, default='日本語') 
parser.add_argument('--drop-id', default=False, action='store_true')
parser.add_argument('--distinct', default=False, action='store_true')
parser.add_argument('--mb2dir', type=Path, default=mb2dir)


if __name__ == '__main__':
    args = parser.parse_args()
    print(args)
    if args.outdir is None:
        args.outdir = Path(f'ModLangs/{args.target_module}')
        with args.outdir.joinpath(f'ModuleData/Languages/{args.langshort}') as fp:
            if not fp.exists():
                fp.mkdir(parents=True)

with args.outdir.joinpath(f'strings_{args.target_module}.po').open('br') as f:
    catalog = read_po(f)
print(type(catalog))
d_new = po2pddf_easy(catalog)
# d_new = pd.read_excel(args.outdir.joinpath(f'strings_{args.target_module}.xlsx'))

xml = BeautifulSoup(
    f'''
    <base>
    <tags>
    <tag language="{args.langid}" />
    </tags>
    <strings>
    </strings>
    </base>
    ''',
    features='lxml-xml')
strings = xml.find('strings')
for i, r in d_new.iterrows():
    strings.append(BeautifulSoup(f'''<string id="{r['id']}" text="{r['text']}" />''', 'lxml-xml'))
with args.outdir.joinpath(f'ModuleData/Languages/{args.langshort}/std_translation-{args.langshort}.xml').open('w', encoding='utf-8') as f:
    f.writelines(xml.prettify(formatter='minimal'))
xml = BeautifulSoup(
    f'''
    <LanguageData id="{args.langid}">
      <LanguageFile xml_path="{args.langshort}/std_translation-{args.langshort}.xml">
    </LanguageData>''',
    features='lxml-xml'
)
with args.outdir.joinpath(f'ModuleData/Languages/{args.langshort}/language_data.xml').open('w', encoding='utf-8') as f:
    f.writelines(xml.prettify(formatter='minimal'))
