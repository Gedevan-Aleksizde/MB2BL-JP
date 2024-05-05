#! /usr/bin/env python3

import argparse
from pathlib import Path
import lxml.etree as ET
from functions import (
    merge_yml,po2pddf_easy
    )
import polib

parser = argparse.ArgumentParser()
parser.add_argument('target_module', type=str)
parser.add_argument('--outdir', type=Path, default=None)
parser.add_argument('--langshort', type=str, default='JP')
parser.add_argument('--langid', type=str, default='日本語') 
parser.add_argument('--distinct', default=False, action='store_true')
parser.add_argument('--output-blank', default=False, action='store_true')
parser.add_argument('--with-id', default=False, action='store_true')
parser.add_argument('--pofile', type=Path, default=None, help='default: <output directory>/strings_<nodule folder name>.po')

if __name__ == '__main__':
    args = parser.parse_args()
    with Path(__file__).parent.joinpath('default.yml') as fp:
        if fp.exists():
            args = merge_yml(fp, args, parser.parse_args(['']))
    if args.outdir is None:
        args.outdir = Path(f'Mods/{args.target_module}')
        with args.outdir.joinpath(f'{args.target_module}/ModuleData/Languages/{args.langshort}') as fp:
            if not fp.exists():
                fp.mkdir(parents=True)
    if args.pofile is None:
        args.pofile = args.outdir.joinpath(f'{args.target_module}.po')
    print(args)

pof = polib.pofile(args.pofile, encoding='utf-8')
d_new = po2pddf_easy(pof, with_id=args.with_id)
if not args.output_blank:
    d_new = d_new.loc[lambda d: d['text'] != '']
# d_new = pd.read_excel(args.outdir.joinpath(f'strings_{args.target_module}.xlsx'))

xml = ET.fromstring(
    f'''
    <base>
    <tags>
    <tag language="{args.langid}" />
    </tags>
    <strings>
    </strings>
    </base>
    ''')
strings = xml.find('strings')
for i, r in d_new.iterrows():
    tmp = ET.fromstring(f'''<string id="PLAHECOLHDER" text="[PLACEHOLDER]" />''')
    tmp.attrib['id']= r['id']
    tmp.attrib['text'] = r['text']
    strings.append(tmp)
xml = ET.ElementTree(xml)
ET.indent(xml, space="  ", level=0)
xml.write(
    args.outdir.joinpath(f'{args.target_module}/ModuleData/Languages/{args.langshort}/strings-{args.langshort}.xml'),
    pretty_print=True, xml_declaration=True, encoding='utf-8')

xml = ET.fromstring(
    f'''
    <LanguageData id="{args.langid}">
      <LanguageFile xml_path="{args.langshort}/strings-{args.langshort}.xml" />
    </LanguageData>'''
)
xml = ET.ElementTree(xml)
ET.indent(xml, space="  ", level=0)
xml.write(
    args.outdir.joinpath(f'{args.target_module}/ModuleData/Languages/{args.langshort}/language_data.xml'),
    pretty_print=True, xml_declaration=True, encoding='utf-8')