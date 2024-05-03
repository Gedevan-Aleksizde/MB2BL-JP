
import argparse
import yaml
from pathlib import Path
import warnings

import pandas as pd
from datetime import datetime
from functions import export_id_text_list


def main():
    file_dir = Path(__file__).parent.joinpath('vanilla-id.csv')
    export_id_text_list(Path('text/MB2BL-JP.po'), file_dir)

if __name__ == '__main__':
    main()