#! /usr/bin/env python3
# encoding: utf-8

from pathlib import Path
import tempfile
import argparse
from bs4 import BeautifulSoup
import shutil
import subprocess
import re

parser = argparse.ArgumentParser()
parser.add_argument('--targetdir', type=Path)
parser.add_argument('--modid', type=str)
parser.add_argument('--xmlpath', type=Path, default=None)
parser.add_argument('--exepath', type=Path, default=Path(r'''C:\Program Files (x86)\Steam\steamapps\common\Mount & Blade II Bannerlord\bin\Win64_Shipping_Client\TaleWorlds.MountAndBlade.SteamWorkshop.exe'''))
args = parser.parse_args(
    #['']
)

tmpdir = Path(tempfile.mkdtemp())
if str(tmpdir).find(' ') >= 0:
    print('omaeniwa murida')
    raise()
print(f'''tmp dir: {tmpdir}''')
if args.xmlpath is None:
    if args.targetdir is None:
        print('either --targetdir or --xmlpath needed')
        raise()
    xml = BeautifulSoup(
        '''<Tasks>
            <GetItem>
            <ItemId Value=""/>
            </GetItem>
        <UpdateItem>
            <ModuleFolder Value = "" />
            <ChangeNotes Value="make inconvenient TW uploader a bit easier">
            <Tags> 
            </Tags>
            <Image />
            <Visibility />
        </UpdateItem>
        </Tasks>''',
        features="lxml-xml"
    )
    mod_path = tmpdir.joinpath(args.targetdir.name)
    if args.modid is None:
        print("Steam Workshop ID must be specified!")
        raise()
    xml.find('ItemId')['Value'] = args.modid
else:
    with args.xmlpath.open('r', encoding='utf-8') as f:
        xml = BeautifulSoup(f, features='lxml-xml')
    thumbnailpath = xml.find('Image').get('Value')
    if thumbnailpath is not None:
        thumbnailpath = Path(thumbnailpath)
        thumbnailpath_new = tmpdir.joinpath(thumbnailpath.name)
        shutil.copy(thumbnailpath, str(thumbnailpath_new))
        xml.find('Image')['Value'] = str(thumbnailpath_new)
    if args.modid is not None:
        xml.find('ItemId')['Value'] = args.modid
    mod_path = tmpdir.joinpath(Path(xml.find('ModuleFolder')['Value']).name)
    args.targetdir = Path(xml.find('ModuleFolder')['Value'])
    
xml.find('ModuleFolder')['Value'] = str(mod_path)

print(f'----- XML settings -----')
print(re.sub('^.+\n', '', xml.prettify(formatter='minimal')))
print(f'------------------------')


tmpdir.joinpath('WorkshopUpdate.xml').open('w', encoding='utf-8').writelines(re.sub('^.+\n', '', xml.prettify(formatter='minimal')))
shutil.copytree(str(args.targetdir), str(mod_path), dirs_exist_ok=True)

subprocess.call([str(args.exepath), tmpdir.joinpath('WorkshopUpdate.xml')], shell=True)

shutil.rmtree(tmpdir)