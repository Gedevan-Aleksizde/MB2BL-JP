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
    xml = BeautifulSoup(
        '''<Tasks><CreateItem />
        <UpdateItem><ModuleFolder Value = "" />
            <ItemDescription Value="Why so inconvenient?"/>
            <Tags> 
            </Tags>
            <Image Value = "" />
            <Visibility Value="Private"/>
        </UpdateItem>
        </Tasks>''',
        features="lxml-xml"
    )
    mod_path = tmpdir.joinpath(args.targetdir.name)
    xml.find('Image')['Value'] = str(mod_path.joinpath('thumbnail.png'))
else:
    with args.xmlpath.open('r', encoding='utf-8') as f:
        xml = BeautifulSoup(f, features='lxml-xml')                
    thumbnailpath = Path(xml.find('Image')['Value'])
    thumbnailpath_new = tmpdir.joinpath(thumbnailpath.name)
    shutil.copy(thumbnailpath, str(thumbnailpath_new))
    xml.find('Image')['Value'] = str(thumbnailpath_new)
    mod_path = tmpdir.joinpath(Path(xml.find('ModuleFolder')['Value']).name)
    args.targetdir = Path(xml.find('ModuleFolder')['Value'])

xml.find('ModuleFolder')['Value'] = str(mod_path)

print(f'----- XML settings -----')
print(re.sub('^.+\n', '', xml.prettify(formatter='minimal')))
print(f'------------------------')

tmpdir.joinpath('WorkshopCreate.xml').open('w', encoding='utf-8').writelines(re.sub('^.+\n', '', xml.prettify(formatter='minimal')))

shutil.copytree(str(args.targetdir), str(mod_path), dirs_exist_ok=True)

subprocess.call([str(args.exepath), tmpdir.joinpath('WorkshopCreate.xml')], shell=True)

shutil.rmtree(tmpdir)