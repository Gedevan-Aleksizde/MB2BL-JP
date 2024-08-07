#! /usr/bin/env python3

import platform
import argparse
from pathlib import Path
import warnings
import pandas as pd
import lxml.etree as ET
import numpy as np
import polib
from datetime import datetime
from functions import (
    pddf2po, po2pddf,
    merge_yml,
    export_id_text_list,
    match_public_id,
    match_string
    )
import hashlib
if platform.system() == "Windows":
    # import winshell
    from win32com.client import Dispatch
import html

parser = argparse.ArgumentParser()
parser.add_argument('target_module', type=str, help='target module folder name')
parser.add_argument('--outdir', type=Path, default=None, help='output folder default is `./Mods`')
parser.add_argument('--langshort', type=str)
parser.add_argument('--langid', type=str)
parser.add_argument('--keep-vanilla-id', default=None, action='store_true',
                    help='ignore vanilla IDs which has potential problems by reusing or abusing in the mod.')
parser.add_argument('--how-distinct', type=str, default=None, help='how making distinct: one of `context`, `file`, `all`. The missing ID is fixed whichever choosed.')
parser.add_argument(
    '--drop-original-language', default=None, action='store_true', help='suppress to merge the own language folder')
parser.add_argument(
    '--pofile', type=Path, default=None,
    help='additional translation file. PO or MO file are available. It requires the same format as what this script outputs') # TODO: 複数のファイルを参照 
parser.add_argument('--mb2dir', type=Path, default=None, help='MB2 install folder')
parser.add_argument('--mo2dir', type=Path, default=None, help='MO2 mods folder, which is serarch if target module is not found in mb2dir')
parser.add_argument('--autoid-prefix', type=str, default=None)
parser.add_argument('--id-exclude-regex', type=str, default=None, help='make ID invalid if this pattern matched')
parser.add_argument('--convert-exclam', default=None, action='store_true')
parser.add_argument('--autoid-digits', default=None, type=int)
parser.add_argument('--dont-clean', default=None, action='store_true')
parser.add_argument('--verbose', default=None, action='store_true')
parser.add_argument('--suppress-shortcut', action='store_true')


FILTERS  = [
    dict(context='Concept.title', xpath='.//Concept[@title][@id]', key='title'),
    dict(context='Concept.description', xpath='.//Concept[@description][@id]', key='description'),
    dict(context='Culture.name', xpath='.//Culture[@name][@id]', key='name'),
    dict(context='Culture.text', xpath='.//Culture[@text][@id]', key='text'),
    dict(context='Culture.femaleName', xpath='.//female_names/name[@name]', key='name'),
    dict(context='Culture.maleName', xpath='.//male_names/name[@name]', key='name'),
    dict(context='Culture.clanName', xpath='.//clan_names/name[@name]', key='name'),
    dict(context='CraftedItem.name', xpath='.//CraftedItem[@name][@id]', key='name'),
    dict(context='CraftingPiece.name', xpath='.//CraftingPiece[@name][@id]', key='name'),
    dict(context='Faction.name', xpath='.//Faction[@name][@id]', key='name'),
    dict(context='Faction.short_name', xpath='.//Faction[@short_name][@id]', key='short_name'),
    dict(context='Faction.text', xpath='.//Faction[@text][@id]', key='text'),
    dict(context='Kingdom.name', xpath='.//Kingdom[@name][@id]', key='name'),
    dict(context='Kingdom.short_name', xpath='.//Kingdom[@short_name][@id]', key='short_name'),
    dict(context='Kingdom.text', xpath='.//Kingdom[@text][@id][@id]', key='text'),
    dict(context='Kingdom.title', xpath='.//Kingdom[@title][@id]', key='title'),
    dict(context='Kingdom.ruler_title', xpath='.//Kingdom[@ruler_title][@id]', key='ruler_title'),
    dict(context='Hero.name', xpath='.//Hero[@text][@id]', key='text'),
    dict(context='Item.name', xpath='.//Item[@name][@id]', key='name'),
    dict(context='ItemModifier.name', xpath='.//ItemModifier[@name][@id]', key='name'),
    dict(context='NPCCharacter.name', xpath='.//NPCCharacter[@name][@id]', key='name'),
    dict(context='NPCCharacter.text', xpath='.//NPCCharacter[@text][@id]', key='text'),
    dict(context='Module_String.string', xpath='.//string[@text][@id]', key='text'),
    dict(context='Settlement.name', xpath='.//Settlement[@name][@id]', key='name'),
    dict(context='Settlement.text', xpath='.//Settlement[@text][@id]', key='text'),
    dict(context='SiegeEngineType.name', xpath='.//SiegeEngineType[@name][@id]', key="name"),
    dict(context='SiegeEngineType.description', xpath='.//SiegeEngineType[@description][@id]', key="description"),
    dict(context='Scene.name', xpath='.//Scene[@name]', key='name'),
    # 以下はBanner Kings独自実装のスキーマ
    dict(context="duchy.name", xpath='.//duchy[@name][@id]', key="name"),
    dict(context="duchy.fullName", xpath='.//duchy[@fullName][@id]', key="fullName"),
    dict(context="WorkshopType.name", xpath='.//WorkshopType[@name][@id]', key="name"),
    dict(context="WorkshopType.jobname", xpath='.//WorkshopType[@jobname][@id]', key="jobname"),
    dict(context="WorkshopType", xpath='.//WorkshopType[@description][@id]', key="description"),
    dict(context="string.title", xpath='.//string[@title][@id]', key="title"),
    dict(context="string.text", xpath='.//string[@text][@id]', key="text"),
    # TODO: Custom Spawn API
    dict(context="NameSignifier.value", xpath='.//NameSignifier[@value]', key="value")
    # TODO: RegularBanditDailySpawnData -> Name, SpawnMessage, DeathMessage
]

# TODO: REFACTORING!!!

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
    print(f'reading XML files from {language_folder}')
    language_files = []
    for lang_data_file in language_folder.rglob('./language_data.xml'):
        xml = ET.parse(lang_data_file)
        print(ET.tostring(xml))
        xml_lang_data = xml.getroot()
        if xml_lang_data.attrib['id'] == target_language:
            for x in xml_lang_data.xpath('./LanguageFile'):
                print(html.unescape((ET.tostring(x, encoding='unicode'))))
            language_files += [language_folder.joinpath(x.attrib['xml_path']) for x in xml_lang_data.xpath('./LanguageFile')]
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
        verbose:bool,
    )->pd.DataFrame:
    """
    # タグはいろいろあるので翻訳対象の条件づけが正確なのかまだ自信がない
    # TODO: ! とか * とか訳のわからんIDを付けているケースが多い. 何の意味が?
    """
    ds = []
    print(f'reading XML and XSLT files from {module_data_dir}')
    for file in module_data_dir.rglob('./*.xml'):
        if file.relative_to(module_data_dir).parts[0].lower() != 'languages':
            d = non_language_xml_to_pddf(file, module_data_dir, verbose)
            print(f"""(not language file) {d.shape[0]} entries found in {file.relative_to(module_data_dir)}.""")
            ds += [d]
    for file in module_data_dir.rglob('./*.xslt'):
        if file.relative_to(module_data_dir).parts[0].lower() != 'languages':
            d = non_language_xslt_to_pddf(file, module_data_dir, verbose)
            print(f"""(not language file) {d.shape[0]} entries found in {file.relative_to(module_data_dir)}.""")
            ds += [d]
    for en_str in ['English', 'EN', '']:
        for file in module_data_dir.glob(f'languages/{en_str}/*.xml'):
            d = langauge_xml_to_pddf(file, 'text_EN', module_data_dir)
            print(f"""(English language file) {d.shape[0]} entries found in {file.relative_to(module_data_dir)}.""")
            if d.shape[0] > 0:
                ds += [d]
    if len(ds) == 0:
        d_return = None
    else:
        d_return = pd.concat(ds)
        d_return = d_return.assign(
            text_EN=lambda d: np.where(d['text_EN'] == '', np.nan, d['text_EN'])
        )
        print(f'''---- {d_return['text_EN'].isna().sum()} entries has blank text. ----''')
        d_return['text_EN'] = d_return['text_EN'].fillna('')
    return d_return


def non_language_xml_to_pddf(fp:Path, base_dir:Path=None, verbose:bool=False)->pd.DataFrame:
    if base_dir is None:
        base_dir = fp.parent
    with base_dir.joinpath(fp).open('r', encoding='utf-8') as f:
        xml = ET.parse(f)
    ds = []
    for filter in FILTERS:
        xml_entries = xml.xpath(filter['xpath'])
        if verbose:
            print(f'''{len(xml_entries)} {filter['context']} attributes found in {filter['name']} tags''')
        if len(xml_entries) > 0:
            tmp = pd.DataFrame(
                [(x.attrib.get('id'), x.attrib[filter['key']], f'''{filter['context']}''') for x in xml_entries],
                columns=['object_id', 'text_EN', 'context']
            ).assign(
                id = lambda d: np.where(
                    d['text_EN'].str.contains(r'^\{=.+?\}.*$', regex=True),
                    d['text_EN'].str.replace(r'^\{=(.+?)\}.*$', r'\1', regex=True),
                    ''
                ),
                file = fp.relative_to(base_dir).as_posix(),
                text_EN = lambda d: d['text_EN'].str.replace(r'^\{=.+?\}(.*)$', r'\1', regex=True),
                attr = filter['key']
            )
            ds += [tmp]
    if len(ds) > 0:
        return pd.concat(ds)
    else:
        return pd.DataFrame(columns=['id', 'text_EN', 'context', 'file', 'attr'])


def non_language_xslt_to_pddf(fp:Path, base_dir:Path=None, verbose:bool=False)->pd.DataFrame:
    if base_dir is None:
        base_dir = fp.parent
    with base_dir.joinpath(fp).open('r', encoding='utf-8') as f:
        xslt = ET.parse(f)
    ds = []
    for filter in FILTERS:
        xslt_entries = xslt.xpath(
            f'''.//xsl:template[contains(@match, "{filter['context'].split('.')[0]}")]/xsl:attribute[@name='{filter["key"]}']''',
            namespaces={'xsl': 'http://www.w3.org/1999/XSL/Transform'})
        # TODO: more rigorous conditioning
        if verbose:
            print(f'''{len(xslt_entries)} {filter['context']} attributes found in {filter['context']} tags''')
        if len(xslt_entries) > 0:
            tmp = pd.DataFrame(
                [(x.text, f'''{filter['context']}''') for x in xslt_entries],
                columns=['text_EN', 'context']
            ).assign(
                id = lambda d: np.where(
                    d['text_EN'].str.contains(r'^\{=.+?\}.*$', regex=True),
                    d['text_EN'].str.replace(r'^\{=(.+?)\}.*$', r'\1', regex=True),
                    ''
                ),
                file = fp.relative_to(base_dir).as_posix(),
                text_EN = lambda d: d['text_EN'].str.replace(r'^\{=.+?\}(.*)$', r'\1', regex=True),
                attr = filter['key']
            )
            ds += [tmp]
    if len(ds) > 0:
        return pd.concat(ds)
    else:
        return pd.DataFrame(columns=['id', 'text_EN', 'context', 'file', 'attr'])


def langauge_xml_to_pddf(fp:Path, text_col_name:str, base_dir:Path=None)->pd.DataFrame:
    if base_dir is None:
        base_dir = fp.parent
    xml = ET.parse(base_dir.joinpath(fp))
    xml_entries = xml.xpath('.//strings/string[@id][@text]')
    if len(xml_entries) > 0:
        d = pd.DataFrame(
            [(x.attrib['id'], x.attrib['text'], 'language.text') for x in xml_entries], columns=['id', text_col_name, 'context']
        ).assign(
            attr = 'string',
            file = fp.relative_to(base_dir).as_posix()
        )
        return d
    else:
        return pd.DataFrame(columns=['id', text_col_name, 'context', 'attr', 'file'])


def generate_id_sha256(text:str=None, n:int=5):
    """
    n: max 32
    """
    n = min(n, 32)
    hash = hashlib.sha256(text.encode()).hexdigest()[-n:]
    binary = bin(int(hash[:32], base=32)).removeprefix('0b')[n:]
    return ''.join([h.upper() if i == '1' else h.lower() for h, i, in zip(hash, binary)])


def normalize_string_ids(
        data:pd.DataFrame,
        how_distinct:str,
        exclude_pattern:str,
        keep_redundancies:bool,
        autoid_digits:int,
        keep_vanilla_id:bool,
        langshort:str,
        convert_exclam:bool,
        autoid_prefix:str)->pd.DataFrame:
    """
    後2つ以外のXML, module_string, language の順で信頼できるはずなので被ったらその優先順位でなんとかする.
    """
    vanilla_id_path = (Path('tools') if '__file__' not in locals() else Path(__file__).parent).joinpath('vanilla-id.csv')
    if keep_redundancies:
        lambda_id = (
        lambda d: np.where(
            (d['id'] == '') | d['id'].isna(),
            [f'{autoid_prefix}' + generate_id_sha256(text, autoid_digits) for text in d['context'] + d['attr'] + d['text_EN']],  # TODO
            d['id']
        )
    )
    else:
        lambda_id = (
        lambda d: np.where(
            (d['id'] == '') | d['id'].isna(),
            [f'{autoid_prefix}' + generate_id_sha256(text + str(i), autoid_digits) for i, text in enumerate(d['context'] + d['attr'] + d['text_EN'])],  # TODO
            d['id']
        )
    )
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
    if not convert_exclam:
        # TODO: なぜ!を付ける人が多いのか? このオプションいるか?
        # TODO: 翻訳が必要ないのは動的に名前が上書きされるテンプレートNPCの名称のみだが, それとは関係なく =! とか =* とか書いている人が多い. なんか独自ルールの記号使ってる人までいる…
        n = data.shape[0]
        data = data.loc[lambda d: d['id'] != '!']
        print(f'''---- {n - data.shape[0]} entries having `!` ID dropped. This is disabled by `--convert_exclam` option. ----''')
        n = data.shape[0]
        data = data.loc[lambda d: d['id'] != '*']
        print(f'''---- {n - data.shape[0]} entries having `*` ID dropped. This is disabled by `--convert_exclam` option. ----''')
        # TODO: precise id detetion
        # TODO: IDに使用できる文字
        # TODO: テンプレートの名前かどうかを確実に判別する方法がない
    if exclude_pattern is not None:
        data = data.assign(
            id = lambda d: np.where(d['id'].str.contains(exclude_pattern, regex=True), '', d['id'])
        )
    if not keep_vanilla_id:
        # テキストを変更しているのにバニラのIDを使いまわしている, あるいは偶然に被っている場合はIDを削除する
        # erase entry if both ID and the original string is the same.
        n = data.loc[lambda d: d['id'] != ''].shape[0]
        data = data.merge(
            vanilla_ids.rename(columns={'text_EN': 'text_EN_original'}),
            on='id', how='left') 
        data = data.assign(
            id = lambda d: np.where(d['id_used_in_vanilla'] & (d['text_EN'] != d['text_EN_original']), '', d['id'])
        )
        print(f'''---- {n - data.loc[lambda d: d['id'] != ''].shape[0]} abused IDs which are used in vanilla are reset. ----''')
        n = data.shape[0]
        data = data.loc[lambda d: ~(d['id_used_in_vanilla'] & (d['text_EN'] == d['text_EN_original']))]
        print(f'''---- {n - data.shape[0]} entries which are identical to vanilla ones dropped. -----''')
        data = data.drop(columns=['text_EN_original', 'id_used_in_vanilla'])
        # TODO: 常にバニラと比較するように
    data = data.assign(missing_id = lambda d: (d['id'].str.contains('^[?!\*]$')) | (d['id'] == '') | (d['id'] == '*'))
    if how_distinct == 'context':
        n = data.shape[0]
        data = data.groupby(['text_EN', 'context', 'attr']).agg(
            {
                'id': lambda s: s.sort_values().iloc[0],
                'file': lambda s: [x for x in s]
            }
        ).reset_index()
        print(f'''---- {n - data.shape[0]} ID errors detected after making distinct by context and attr. ----''')
    elif how_distinct == 'file':
        n = data.shape[0]
        data = data.groupby(['text_EN', 'context', 'attr', 'file']).agg({'id': lambda s: s.sort_values().iloc[0]}).reset_index()
        data['file'] = [[x] for x in data['file']]
        print(f'''---- {n - data.shape[0]} ID errors detected after making distinct by context and files. ----''')
    else:
        errors = data.loc[lambda d: (d['id'] == '') | d['id'].isna()].shape[0]
        data['file'] = [[x] for x in data['file']]
        print(f'''---- {errors} missing IDs detected ----''')
    n = data.shape[0]
    data = data.drop_duplicates(['id', 'text_EN'])
    print(f'''{n - data.shape[0]} duplicated entries are dropped''')
    data = data.assign(id=lambda_id)
    return data


def merge_language_file(
        data:pd.DataFrame,
        data_language:pd.DataFrame=None,
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
        data['text'] = None
    if data_po is not None and data_po.shape[0] > 0:
        data_po = data_po.drop(columns=['attr', 'locations', 'context'], errors='ignore')
        data = data.merge(data_po, on=['id', 'text_EN'], how='left')
        data = data.assign(
            text = lambda d: np.where(d['text_x'].isna(), d['text_y'], d['text_x'])
            ).drop(columns=['text_x', 'text_y'])
        if translation_merge_on in ['id', 'both']:
            data = data.merge(data_po.rename(columns={'text_EN': 'text_EN_po'}), on=['id'], how='left')
            data = data.assign(
                text=lambda d: np.where(d['text_x'].isna(), d['text_y'], d['text_x']),
                flags=lambda d: np.where(d['text_x'].isna(), [{'fuzzy'} | set() if type(s) is not set else s for s in d['flags_y']], [set() if type(s) is not set else s for s in d['flags_y']]),
                notes=lambda d: d['notes_x'] + d['notes_y']
            )
            data = data.assign(
                flags=lambda d: np.where((d['text_EN_po'] == d['text_EN']) & ~(d['text'].isna()), [s - {'fuzzy'} for s in d['flags']], d['flags'])
            ).drop(columns=['text_x', 'text_y', 'flags_x', 'flags_y', 'notes_x', 'notes_y', 'text_EN_po'])
        if translation_merge_on in ['string', 'both']:
            data = data.merge(data_po.rename(columns={'id': 'id_po'}), on=['text_EN'], how='left')
            data = data.assign(
                text=lambda d: np.where(d['text_x'].isna(), d['text_y'], d['text_x']),
                flags=lambda d: np.where(d['text_x'].isna(), [{'fuzzy'} | set() if type(s) is not set else s for s in d['flags_y']], [set() if type(s) is not set else s for s in d['flags_y']]),
                notes=lambda d: d['notes_x'] + d['notes_y']
            )
            data = data.assign(
                flags=lambda d: np.where((d['id'] == d['id_po']) & ~(d['text'].isna()), [s - {'fuzzy'} for s in d['flags']], d['flags'])
            ).drop(columns=['text_x', 'text_y', 'flags_x', 'flags_y', 'notes_x', 'notes_y', 'id_po'])
        data['notes'] = [x if type(x) is list else [] for x in data['notes']]
        data['text'] = data['text'].fillna('')
        data = data.assign(flags=lambda d: np.where(d['text'] == '', [s | {'fuzzy'} for s in d['flags']], d['flags']))
    return data


def export_corrected_xml_xslt_id(data:pd.DataFrame, module_data_dir:Path, dont_clean:bool, outdir:Path, target_module:str, filetype:str)->None:
    """
    read and correct wrong IDs in XML/XSLT files, and export them
    """
    n_changed_files = 0
    for file in module_data_dir.rglob(f'./*.{filetype}'):
        print(f"""checking {file.relative_to(module_data_dir)}""")
        any_changes = False
        if file.relative_to(module_data_dir).parts[0].lower() != 'languages':            
            with file.open('r', encoding='utf-8') as f:
                xml = ET.parse(f)
            for filter in FILTERS:
                if filetype == "xml":
                    xml_entries = xml.xpath(filter['xpath'])
                elif filetype == "xslt":
                    xml_entries = xml.xpath(
                        f'''.//xsl:template[contains(@match, "{filter['context'].split('.')[0]}")]/xsl:attribute[@name={filter['key']}]''',
                        namespaces={'xsl': 'http://www.w3.org/1999/XSL/Transform'})
                    # xml_entries = [x for x in xml_entries if x is not None]
                d_sub = (
                    data.loc[
                        lambda d: (
                            d['context'] == f"""{filter['context']}""")|
                            (d['context'].isin(['module.string', 'text.string']))
                    ]
                    .assign(
                        new_string = lambda d: '{=' + d['id'] + '}' + d['text_EN']
                    )
                )
                for entry in xml_entries:
                    if filetype == "xslt":
                        old_string = entry.text
                    else:
                        old_string =  entry.attrib[filter['key']]
                    entry_id = match_public_id.sub(r'\1', old_string) 
                    entry_text = match_string.sub(r'\1', old_string)
                    r = d_sub[lambda d: (d['id'] != entry_id) & (d['text_EN'] == entry_text)].reset_index()
                    if r.shape[0] > 0:
                        any_changes = True
                        print(f'''{entry_id}/{entry_text} -> {r.shape[0]}, {r['new_string']}''')
                        if filetype == "xml":
                            entry = replace_id_xml(entry, attr=filter['key'], new_string=r['new_string'][0])
                        elif filetype == "xslt":
                            entry = replace_id_xslt(entry, attr=filter['key'], new_string=r['new_string'][0])
                        else:
                            Warning("Incorrect file type")
        if any_changes:
            n_changed_files += 1
            print(f'{file.name} is needed to be overwritten')
            outfp = outdir.joinpath(f'{target_module}/ModuleData/{file.relative_to(module_data_dir)}')
            if not dont_clean and outfp.exists():
                print(f'deleting output old {outfp.name}')
                outfp.unlink()
            with outfp.parent as fdir:
                if not fdir.exists():
                    fdir.mkdir(parents=True, exist_ok=True)
            ET.indent(xml, space="  ", level=0)
            xml.write(outfp, pretty_print=True, xml_declaration=True, encoding='utf-8')
        any_changes = False
    print(f'''{n_changed_files} {filetype.upper()} files exported''')


def replace_id_xml(entry:ET.Element, attr:str, new_string:str)->ET.Element:
    entry.attrib[attr] = new_string
    return entry


def replace_id_xslt(entry:ET.Element, attr:str, new_string:str)->ET.Element:
    print(entry)
    entry.text = new_string
    return entry


def read_po_as_df(pofile:Path)->pd.DataFrame:
    if pofile.exists():
        pof = polib.pofile(pofile)
    elif pofile.with_suffix('.mo').exists():
        pof = polib.mofile(pofile.with_suffix('.mo'))
        print(f"{pofile.with_suffix('.mo')} loaded insteadly")
    return po2pddf(pof, drop_prefix_id=False)


def main():
    module_data_dir = args.mb2dir.joinpath(f'Modules/{args.target_module}/ModuleData')
    module_data_dir = module_data_dir.resolve()
    if not module_data_dir.exists():
        globs = list(args.mo2dir.resolve().expanduser().glob(f'*/{args.target_module}/ModuleData'))
        if len(globs) > 0:
            module_data_dir = globs[0]
            warnings.warn(f'''{args.target_module} not found in MB2 directory, load files from {module_data_dir} instead.''')
        else:
            raise(f'''{module_data_dir} not found!''')
    d_mod = extract_all_text_from_xml(module_data_dir, args.verbose)
    n = d_mod.shape[0]
    print(f'''---- {n} entries detected from this mod ----''')
    d_mod = normalize_string_ids(
        data=d_mod,
        how_distinct=args.how_distinct, exclude_pattern=args.id_exclude_regex,
        keep_redundancies=args.keep_redundancies,
        autoid_digits=args.autoid_digits,
        keep_vanilla_id=args.keep_vanilla_id,
        langshort=args.langshort, convert_exclam=args.convert_exclam, autoid_prefix=args.autoid_prefix)
    print(f'''---- {d_mod.shape[0]} entries left. ----''')
    print(f"---- Extract {args.langid} strings from ModuleData/Lanugages/ folders.----")
    d_mod_lang = read_mod_languages(args.langid, module_data_dir.joinpath('Languages'))
    print(f'''---- {d_mod_lang.shape[0]} entries found. ----''')
    if args.pofile is not None:
        if args.pofile.exists():
            d_po = read_po_as_df(args.pofile).drop(columns=['duplication'])
        else:
            warnings.warn(f'''{args.pofile} not found''')
            d_po = None
    else:
        print('---- PO file not specified. mergeing with previous translation skipped. ----')        
        d_po = None
    d_mod = merge_language_file(
        d_mod,
        None if args.drop_original_language else d_mod_lang,
        d_po,
        'both')
    if 'text' not in d_mod.columns:
        d_mod['text'] = ''
    for filetype in ['xml', 'xslt']:
        print(f'''---- Checking {filetype.upper()} files ----''')
        export_corrected_xml_xslt_id(d_mod, module_data_dir, dont_clean=args.dont_clean, outdir=args.outdir, target_module=args.target_module, filetype=filetype)
    if 'flags' in d_mod:
        d_mod = d_mod.assign(flags=lambda d: [list(s) for s in d['flags']])
    else:
        d_mod = d_mod.assign(flags=lambda d: [['fuzzy']] * d.shape[0])
    pof = pddf2po(
        d_mod, with_id=False, make_distinct=False, regacy_mode=False,
        col_id_text='text_EN', col_text='text', col_comments='note', col_context='context', col_locations='file', col_flags='flags')
    with args.outdir.joinpath(f'{args.target_module}.xlsx') as fp:
        if fp.exists():
            backup_fp = fp.parent.joinpath(
                f"""BAK/{fp.with_suffix('').name}-{datetime.now().strftime("%Y-%m-%dT%H-%M-%S")}.xlsx"""
            )
            if not backup_fp.parent.exists():
                backup_fp.parent.mkdir()
            print(f"""old file is renamed and moved to BAK/{backup_fp.name}""")
            fp.rename(backup_fp)
        d_mod.to_excel(fp, index=False)
    with args.outdir.joinpath(f'{args.target_module}.po') as fp:
        if fp.exists():
            backup_fp = fp.parent.joinpath(
                f"""BAK/{fp.with_suffix('').name}-{datetime.now().strftime("%Y-%m-%dT%H-%M-%S")}.po"""
            )
            if not backup_fp.parent.exists():
                backup_fp.parent.mkdir()
            print(f"""old file is renamed and moved to BAK/{backup_fp.name}""")
            fp.rename(backup_fp)
        pof.save(fp)
    if platform.system() == 'Windows' and not args.suppress_shortcut:
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(str(args.outdir.joinpath(f"{args.target_module}.lnk")))
        shortcut.Targetpath =  str(module_data_dir.parent)
        shortcut.WorkingDirectory = str(module_data_dir.parent)
        shortcut.save()


if __name__ == '__main__':
    args = parser.parse_args()
    with (Path('tools') if '__file__' not in locals() else Path(__file__).parent).joinpath('default.yml') as fp:
        if fp.exists():
            args = merge_yml(fp, args, parser.parse_args(['']))
    if args.outdir is None:
        args.outdir = Path(f'Mods/{args.target_module}')
        with args.outdir.joinpath(f'{args.target_module}/ModuleData/Languages/{args.langshort}') as fp:
            if not fp.exists():
                fp.mkdir(parents=True)
    if args.autoid_prefix is None:
        args.autoid_prefix = args.target_module.encode('ascii', errors='ignore').decode().replace(' ', '')
    if not args.how_distinct in ['context', 'file', 'all']:
        warnings.warn(f'--how-distinct={args.how_distinct} is invalid value! it should be one of `context`, `file`, or `all`. now `context` used ', UserWarning)
        args.how_distinct = 'context'
    if args.pofile is None:
        args.pofile = args.outdir.joinpath(f'{args.target_module}.po')
    print(args)
    main()


# TODO: Mod ですらIDを重複させてくるやつがいる
# TODO: バニラとかぶってるID
# TODO: 結合方法の確認
# TODO: % のエスケープ
