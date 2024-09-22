#! /usr/bin/env python3

# XMLを読み取って翻訳用のモジュールを作る
# 実装に極度の問題のあるMod対策

from pathlib import Path
import pandas as pd
import lxml.etree as ET
from typing import Iterable, List, Tuple
import argparse
from functions import FILTERS

parser = argparse.ArgumentParser()
parser.add_argument('target_module', type=str, help='target module folder name')
parser.add_argument('--out', type=Path, help='target module folder name', default=None)


def output_all_xslts(data: pd.DataFrame, output_dir: Path) -> bool:
    """
    xml name id ごとに異なるファイルに出力する
    """
    for xml_name_id in data['xml_name_id'].unique():
        d_sub = data.loc[lambda d: d['xml_name_id'] == xml_name_id]
        output_xslt(output_dir.joinpath(f'{xml_name_id.lower()}.xslt'), d_sub['xslt'])


def output_xslt(fp: Path, xslt_entries: Iterable[str]) -> bool:
    """
    テキスト一覧からModuleData修正用のXSLTファイルを生成して書き込む
    """
    xslt_header = '''<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="2.0">
    <xsl:output omit-xml-declaration="yes"/>
    <xsl:template match="node()|@*">
        <xsl:copy>
            <xsl:apply-templates select="node()|@*"/>
        </xsl:copy>
    </xsl:template>'''
    xslt_footer = '''</xsl:stylesheet>'''
    with fp.open('w', encoding='utf-8') as f:
        f.write(f'''{xslt_header}\n''')
        for x in xslt_entries:
            f.write(f'''\t{x}\n''')
        f.write(xslt_footer)
    return True


def output_translation_file(
    fp: Path,
    data: pd.DataFrame,
    col_loc_id: str = 'loc_id',
    col_text: str = 'text',
    lang_name: str = 'English'
) -> bool:
    """
    言語ファイルを生成して書き込む
    """
    xml_header = f'''<?xml version='1.0' encoding='UTF-8'?>
<base>
    <tags>
        <tag language="{lang_name}"/>
    </tags>
    <strings>'''
    xml_footer = '''   </strings>
</base>'''
    with fp.open('w', encoding='utf-8') as f:
        f.write(f'''{xml_header}\n''')
        for _, r in data.iterrows():
            f.write(f'''\t<string id="{r[col_loc_id]}" text="{r[col_text]}" />\n''')
        f.write(xml_footer)
    return True

def output_language_files(lang_dir: Path, fname: str = 'language_data.xml') -> bool:
    """
    language_data.xml を出力する. output_dir には Languages/EN フォルダを指定する.
    """
    lang_data_header = '''<?xml version='1.0' encoding='UTF-8'?>
<LanguageData id="English">
    <LanguageFile xml_path="EN/strings-EN.xml"/>
</LanguageData>
'''
    fp = lang_dir.joinpath(fname)
    fp.open('w', encoding='utf-8').write(lang_data_header)
    return True


def output_submodule(
    module_dir: Path,
    xml_nodes: List[Tuple[str, str]]
) -> bool:
    """
    SubModule.xml を出力する

    xmls_nodes のタプルは (<id>, <path>) で与える
    """
    xml_header = """<?xml version="1.0" encoding="UTF-8"?>
<Module>
	<Name value="<MODULE NAME HERE>"/>
	<Id value="<MODULE ID HERE>"/>
	<Version value="v1.0.0" />
	<DefaultModule value="false"/>
	<SingleplayerModule value="true"/>
	<MultiplayerModule value="false"/>
	<Official value="false"/>
	<DependedModuleMetadatas>
		<DependedModuleMetadata id="<DEPNDING MODULE ID HERE>" order="LoadBeforeThis" />
		<DependedModuleMetadata id="<OTHER OPTIONAL MODULE ID HERE>" order="LoadBeforeThis" optional="true" />
	</DependedModuleMetadatas>
	<Xmls>"""
    xml_footer = """    </Xmls>
</Module>"""
    with module_dir.joinpath('SubModule.xml').open('w', encoding='utf-8') as f:
        f.write(f'''{xml_header}\n''')
        for xml_id, xml_path in xml_nodes:
            f.write(f'''{xml_node(xml_id, xml_path)}\n''')
        f.write(xml_footer)
    return True


def xml_node(xml_id: str, xml_path: str) -> str:
    """
    a
    """
    string = f"""<XmlNode>
    <XmlName id="{xml_id}" path="{xml_path}" />
    <IncludedGameTypes>
        <GameType value="Campaign"/>
        <GameType value="CampaignStoryMode"/>
	</IncludedGameTypes>
</XmlNode>"""
    return string


def xml_format(loc_id:str, name:str) -> str:
    return f'''<string id="{loc_id}" text="{name}"/>'''

def xsl_format_strings(
    xpath_str: str,
    attrib_name: str,
    object_id:str,
    loc_id:str,
    text:str
) -> str:
    """
    テキストの置換用XSLコードを返す
    """
    return f'''<xsl:template match="{xpath_str}[@id='{object_id}']/@{attrib_name}"><xsl:attribute name="{attrib_name}">{{={loc_id}}}{text}</xsl:attribute></xsl:template>'''


def is_in_language_dir(file_path: Path, module_dir: Path) -> bool:
    language_dir = get_language_folder(module_dir)
    try:
        flag = file_path.relative_to(language_dir).parts[0].lower() != 'anguages'
    except ValueError:
        flag = False
    return flag


def get_language_folder(module_dir: Path) -> Path:
        return module_dir.joinpath('ModuleData/Languages')


def extract_entries_to_translate(file_path: Path) -> pd.DataFrame:
    """
    ファイルを読み取って翻訳箇所のID, 原文, ローカリゼーションIDなどをテーブルにして返す
    Returns: 以下のカラムを持っている
        id: ModuleDataのID
        loc_id: ローカリゼーションID
        text: 原文
        xml_name_id: 対応する XmlName id
        context
        xpath
    """
    xml = ET.parse(file_path)
    xml_root = xml.getroot()
    ds: List[pd.DataFrame] = []
    for params in FILTERS:
        d_xmls = (
            pd.DataFrame(
                [(x.attrib.get('id'), x.attrib.get(params['key'])) for x in xml_root.xpath(params['xpath'])], columns=['id', 'text']
            )
            .assign(
                loc_id = lambda d: d['text'].str.replace(r'^\{=(.+?)\}(.+?)$', r'\1', regex=True),  #???
                name = lambda d: d['text'].str.replace(r'^\{=(.+?)\}(.+?)$', r'\2', regex=True)
            )
        )
        d_xmls = d_xmls.assign(
            context=params['context'],
            xpath=params['xpath'],
            xml_name_id=params['xml_name_id'],
            xml_path_to_output=f'''{params['xml_name_id']}/{params['xpath'].split('[')[0][2:].split('.')[0].strip('/')}'''  # TODO
        )
        d_xmls = d_xmls.assign(
            # text_with_id=lambda d: [f'''{{={r['loc_id']}}}{r['name']}''' for i, r in d.iterrows()],
            xslt=lambda d: [
                xsl_format_strings(
                    r['xml_path_to_output'],
                    params['key'],
                    r['id'],
                    r['loc_id'],
                    r['name']
                ) for i, r in d.iterrows()
            ]
        )
        ds += [d_xmls]
    return pd.concat(ds)


def main(module_dir: Path, output_dir: Path) -> bool:
    """
    読み込んだ内容は xml name id ごとにXSLTファイルを分けて書き込む
    args:
        module_dir (Path): モジュールのフォルダパス
        output_dir (Path): 出力先のModuleData, 上書き防止のため通常は別のフォルダを想定する
    """
    moduledata_dir = module_dir.joinpath('ModuleData')
    files = list(
        filter(lambda x: not is_in_language_dir(x, module_dir), [fp for fp in moduledata_dir.rglob("*.xml")])
    )
    if len(files) == 0:
        print('no XML files found!')
        return False
    ds: List[pd.DataFrame] = []
    for fp in files:
        fp_relative = fp.relative_to(moduledata_dir)
        print(f'reading {fp_relative}')
        d = extract_entries_to_translate(fp)
        d = d.assign(file=fp_relative)
        ds += [d]
    d = pd.concat(ds)
    del ds
    d = d.sort_values(['xpath', 'context', 'file'])
    output_all_xslts(d, output_dir)
    output_dir_lang = output_dir.joinpath('Languages/EN')
    if not output_dir_lang.exists():
        output_dir_lang.mkdir(parents=True, exist_ok=True)
    output_translation_file(output_dir_lang.joinpath('strings_EN.xml'), d, 'loc_id', 'name')
    output_language_files(output_dir_lang)
    output_submodule(output_dir.parent, [(x, f'{x.lower()}') for x in d['xml_name_id'].unique() ])
    return True

if __name__ == '__main__':
    args = parser.parse_args()
    print(args)
    args.input_dir = Path().cwd().joinpath(f'Mods/{args.target_module}/{args.target_module}')
    if args.out is None:
        args.out = args.input_dir.parent.joinpath(f'{args.input_dir.name}-l10n/ModuleData')
    if not args.out.exists():
        args.out.mkdir(parents=True, exist_ok=True)
    main(args.input_dir, args.out)
