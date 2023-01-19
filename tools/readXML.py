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
    d[lang][f'text_{lang}_original'] = d[lang][f'text_{lang}_original'].str.replace('[\u00a0\u180e\u2007\u200b\u200f\u202f\u2060\ufeff]', '', regex=True)
# TODO: do you really want to use control letters?
d['JP']['file'] = d['JP']['file'].str.replace(r'^(.+)-jpn\.xml', r'\1.xml', regex=True)
d_bilingual = d['EN'].merge(d['JP'], on=['id', 'file', 'module'], how='left')
d_bilingual = d_bilingual[
    ['module', 'file', 'id', 'text_EN'] + [x for x in d_bilingual.columns if (x[:5] == 'text_' and x[-2:] != 'EN')]
].sort_values(['id', 'file'])
print(f'new text has {d_bilingual.shape[0]} entries')

with Path('text/languages-old.xlsx') as fp:
    if fp.exists():
        d_old = pd.read_excel(fp)
        d_old = d_old[['module', 'id', 'file'] + [x for x in d_old if x[:5] == 'text_']]
        n = d_bilingual.merge(d_old, on=['module', 'file', 'id'], how='inner').shape[0]
        d_bilingual =  d_bilingual.merge(
            d_old.rename(columns={
                f'text_EN': 'text_EN_old',
                f'text_{lang}_original': f'text_{lang}_original_old'}),
            on=['module', 'file', 'id'],
            how='left'
            )
        print(f'{d_bilingual.shape[0] - n} entries are not matched with the old data')
        d_bilingual[
            ['module', 'file', 'id', 'text_EN_old', f'text_{lang}_original_old', f'text_{lang}', 'text_EN', f'text_{lang}_original']
            ].assign(
                updated_en=lambda d: d['text_EN'] != d['text_EN_old'],
                updated_jp=lambda d: d['text_JP_original'] != d['text_JP_original_old']
                ).to_excel('languages.xlsx', index=False)
d_bilingual.to_excel('languages.xlsx', index=False)