import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import argparse

output = Path('Modules')
# TODO: 本体に上書きしてしまうのでバックアップがしたほうがいい
mb2dir = Path('C:\Program Files (x86)\Steam\steamapps\common\Mount & Blade II Bannerlord')

modules = [
    'Native',
    'SandBox',
    'MultiPlayer',
    'CustomBattle',
    'SandBoxCore',
    'StoryMode',
    ]

parser = argparse.ArgumentParser()
parser.add_argument("--input", type=Path, default=Path('text/languages.xlsx'))
parser.add_argument("--output", type=Path, default=output)
parser.add_argument('modules', nargs='*', default=modules)
parser.add_argument('--lang', type=str, default='JP')
parser.add_argument('--langsuffix', type=str, default='jpn')  # 統一してくれ...

if __name__ == '__main__':
    args = parser.parse_args()

df_correct = pd.read_excel(args.input)

# Language ファイルが作用できるのは同一モジュール内のみ. パッチを当てるような適用は不可?.
# XMLファイルのみでは結局本体のファイルを上書きしないとローカライゼーションができない?

# TODO: refactoring

file_list = []
count_total = 0
count_total_denom = 0
for module in args.modules:
    with mb2dir.joinpath('Modules').joinpath(module).joinpath(f"ModuleData/Languages/{args.lang}") as dp:        
        for fp in dp.glob('*.xml'):
            count = 0
            if(fp.name not in ['language_data.xml', 'jp_functions.xml']):
                file_name_en = f'''{fp.with_suffix('').name[:-4]}.xml'''
                d = df_correct.loc[lambda d: (d['file'] == file_name_en) & (d['module'] == module) & ~(d[f'text_{args.lang}'].isna())]
                with fp.open('r', encoding='utf-8') as f:
                    xml = BeautifulSoup(f, 'lxml-xml')
                    if(xml.find('string') is not None):
                        for x in xml.find('strings').find_all('string'):
                            new_strings = d.loc[lambda d: d['id'] == x.get('id'), f'text_{args.lang}'].values
                            if(len(new_strings) > 0):
                                x['text'] = new_strings[0]
                                count += 1
                            if(len(new_strings) > 1):
                                print(f'''ID duplication in {module} module, ID={x.get('id')}''')
            if count > 0:
                count_total += count
                count_total_denom += len(list(xml.strings))
                print(f'''{fp.name} has {count} changed text ({count/len(list(xml.strings)):.2f}%)''')
                with output.joinpath(f'{module}/ModuleData/Languages/{args.lang}/{fp.name}') as newfp:
                    newfp.parent.mkdir(exist_ok=True, parents=True)
                    if newfp.exists():
                        print(f'{fp.name} already exists')
                    with newfp.open('w', encoding='utf-8') as f:
                        f.writelines(xml.prettify())
                    print(f'new translation file created: module={module}, filename={fp.name}')
                file_list += [fp.name]
print(f'''Totally corrected strings account for {count_total/count_total_denom:.2f} of the all text''')
