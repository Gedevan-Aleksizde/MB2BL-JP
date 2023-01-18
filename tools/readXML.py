import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import argparse

mb2dir = Path('C:\Program Files (x86)\Steam\steamapps\common\Mount & Blade II Bannerlord')

modules = [
    'Native',
    'SandBox',
    'MultiPlayer',
    'CustomBattle',
    'SandBoxCore',
    'StoryMode',
    ]

langs = ['JP']
# *_functions.xml?

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('modules', nargs='*', default=modules)
    args = parser.parse_args()

d = dict()
d['EN'] = []
for lang in langs:
    d[lang] = []
    for module in args.modules:
        with mb2dir.joinpath('Modules').joinpath(module).joinpath("ModuleData/Languages") as dp:        
            for fp in dp.joinpath(lang).glob("*.xml"):
                print(fp)
                with fp.open('r', encoding='utf-8') as f:
                    xml = BeautifulSoup(f)
                if(xml.find('strings') is not None):
                    d[lang] += [pd.DataFrame(
                        [(x.get('id'), x.get('text')) for x in xml.find('strings').find_all('string')],
                        columns=['id', f'text_{lang}_original']
                        ).assign(file=fp.name, module=module)
                    ]
            for fp in dp.glob('*.xml'):
                with fp.open('r', encoding='utf-8') as f:
                    xml = BeautifulSoup(f)
                    if(xml.find('string') is not None):
                        d['EN'] += [pd.DataFrame(
                            [(x.get('id'), x.get('text')) for x in xml.find('strings').find_all('string')],
                            columns=['id', f'text_EN']
                            ).assign(file=fp.name, module=module)
                            ]
d['EN'] = pd.concat(d['EN'])
d['EN'] = d['EN'].assign(text_EN = lambda d: d['text_EN'].str.replace('[\u00a0\u180e\u2007\u200b\u200f\u202f\u2060\ufeff]', '', regex=True))
for lang in langs:
    d[lang] = pd.concat(d[lang])
    d[lang][f'text_{lang}'] = d[lang][f'text_{lang}'].str.replace('[\u00a0\u180e\u2007\u200b\u200f\u202f\u2060\ufeff]', '', regex=True)
# そんなに制御文字入れる必要ある?
# なぜか重複しているIDが大量にある. ID なのに. 念のためファイル名でも対応させる
d['JP']['file'] = d['JP']['file'].str.replace(r'^(.+)-jpn\.xml', r'\1.xml', regex=True)
d_bilingual = d['EN'].merge(d['JP'], on=['id', 'file', 'module'], how='left')
d_bilingual[
    ['id', 'text_EN'] + [x for x in d_bilingual.columns if (x[:5] == 'text_' and x[-2:] != 'EN')] + ['file', 'module']
].sort_values(['id', 'file']).to_excel('csv/languages.xlsx', index=False)

a = pd.read_excel("languages.ods", engine='odf')

d_bilingual[
    ['id', 'text_EN'] + [x for x in d_bilingual.columns if (x[:5] == 'text_' and x[-2:] != 'EN')] + ['file', 'module']
].sort_values(['id', 'file']).merge(a.assign(module='Native'), on=['text_EN', 'id', 'file', 'module'], how='left').to_excel('aaaa.xlsx', index=False)