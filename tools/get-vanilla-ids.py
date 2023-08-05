
import argparse
import yaml
from pathlib import Path
import warnings

import pandas as pd
from bs4 import BeautifulSoup
import regex
import numpy as np
from babel.messages.pofile import read_po, write_po
from babel.messages.mofile import read_mo, write_mo
from datetime import datetime
from functions import export_id_text_list


def main():
    file_dir = Path(__file__).parent.joinpath('vanilla-id.csv')
    export_id_text_list(Path('text/MB2BL-JP.po'), file_dir)

if __name__ == '__main__':
    main()