#! /usr/bin/env python3

import argparse
import yaml
from pathlib import Path
import warnings

import pandas as pd
from bs4 import BeautifulSoup
import regex
import numpy as np
from functions import (
    merge_yml, read_xmls, check_duplication, escape_for_po,
    po2pddf_easy, pddf2po
    )
from babel.messages.pofile import read_po, write_po

parser = argparse.ArgumentParser()
parser.add_argument('target_module', type=str)
parser.add_argument('--outdir', type=Path, default=None)
parser.add_argument('--langshort', type=str, default='JP')
parser.add_argument('--langid', type=str, default='日本語') 
parser.add_argument('--distinct', default=False, action='store_true')
parser.add_argument('--output-blank', default=False, action='store_true')
parser.add_argument('--with-id', default=False, action='store_true')
parser.add_argument('--po', type=Path, default=None, help='default: <output directory>/strings_<nodule folder name>.po')

if __name__ == '__main__':
    args = parser.parse_args()
    with Path(__file__).parent.joinpath('default.yml') as fp:
        if fp.exists():
            args = merge_yml(fp, args, parser.parse_args(['']))
    if args.outdir is None:
        args.outdir = Path(f'Mods/{args.target_module}')
        with args.outdir.joinpath(f'ModuleData/Languages/{args.langshort}') as fp:
            if not fp.exists():
                fp.mkdir(parents=True)
    if args.po is None:
        args.po = args.outdir.joinpath(f'strings_{args.target_module}.po')
    print(args)

with args.po.open('br') as f:
    catalog = read_po(f)
d_new = po2pddf_easy(catalog, with_id=args.with_id)
if not args.output_blank:
    d_new = d_new.loc[lambda d: d['text'] != '']
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
