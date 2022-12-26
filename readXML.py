import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path

modroot = "CorrectLocalizationJP"

langs = ['EN', 'JP']
# *_functions.xml?

with Path(modroot).joinpath("ModuleData/Languages") as dp:
    d = dict()
    for lang in langs:
        d[lang] = []
        for fp in dp.joinpath(lang).glob("*.xml"):
            print(fp)
            with fp.open('r', encoding='utf-8') as f:
                xml = BeautifulSoup(f)
            if(xml.find('strings') is not None):
                d[lang] += [pd.DataFrame(
                    [(x.get('id'), x.get('text')) for x in xml.find('strings').find_all('string')],
                    columns=['id', f'text_{lang}']
                    ).assign(file=fp.name)
                ]
        d[lang] = pd.concat(d[lang])
d_bilingual = d['EN'].merge(d['JP'].drop('file', axis=1), on=['id'], how='left')
d_bilingual[
    ['text_EN'] + [x for x in d_bilingual.columns if x[:5] == 'text_' and x[-2:] != 'EN' ] + ['id', 'file']
    ].to_csv('languages.csv', index=False)