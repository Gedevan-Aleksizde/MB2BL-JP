#! /usr/bin/env python3
# encoding: utf-8
import argparse
import html
import warnings
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import lxml.etree as ET
import pandas as pd
import polib
from functions import merge_yml, po2pddf, public_po, removeannoyingchars

pofile = Path("text/MB2BL-Jp.po")
output = Path("Modules")

modules = [
    "DedicatedCustomServerHelper",
    "SandBoxCore",
    "SandBox",
    "MultiPlayer",
    "CustomBattle",
    "StoryMode",
    "BirthAndDeath",
    "Native",
    "FastMode",
]

parser = argparse.ArgumentParser()
parser.add_argument("--input", type=Path, default=pofile)
parser.add_argument("--output", type=Path, default=output)
parser.add_argument("--mb2dir", type=str, default=None)
parser.add_argument("--modules", nargs="*", default=modules)
parser.add_argument("--langshort", type=str, default=None)
parser.add_argument("--langfolder-output", type=str, default=None)
parser.add_argument("--langsuffix", type=str, default="jpn")
parser.add_argument(
    "--functions", type=str, default="jp_functions.xml"
)  # why so diverse country codes used??
parser.add_argument("--langid", type=str, default=None)
parser.add_argument("--langalias", type=str, default=None)
# parser.add_argument('--langname', type=str, default='日本語')
parser.add_argument("--subtitleext", type=str, default="jp")
parser.add_argument("--iso", type=str, default=None)
parser.add_argument("--output-type", type=str, default="module")
parser.add_argument(
    "--with-id",
    default=None,
    action="store_true",
    help="append IDs to strings for debugging",
)
parser.add_argument(
    "--all-entries",
    default=None,
    action="store_true",
    help="to output unchanged entries",
)
parser.add_argument(
    "--skip-blank_vanilla",
    default=None,
    action="store_true",
    help="to suprress to output bkank entries",
)
parser.add_argument(
    "--distinct",
    default=None,
    action="store_true",
    help="drop duplicated IDs in non-Native modules",
)
parser.add_argument(
    "--no-english-overwriting",
    default=None,
    action="store_true",
    help="for M&B weird bug",
)
parser.add_argument(
    "--legacy_id",
    action="store_true",
    help="depricated. for old version of this script",
)
parser.add_argument(
    "--suppress-missing-id",
    default=False,
    action="store_true",
    help="to supress to output unmatched IDs",
)
parser.add_argument(
    "--dont-clean",
    default=False,
    action="store_true",
    help="to keep old files in the output folder",
)
parser.add_argument("--missing-modulewise", default=True, action="store_true")
parser.add_argument(
    "--filename-sep-version",
    default=None,
    type=str,
    help="`1.0`, `1.1` or `1.2`. Why the file names changed at random?",
)
parser.add_argument(
    "--verbose", default=None, action="store_true", help="output verbose log"
)


def main():
    args = parser.parse_args()
    fp = Path(__file__).parent.joinpath("default.yml")
    if fp.exists():
        args = merge_yml(fp, args, parser.parse_args([]))
    if args.langfolder_output is None:
        args.langfolder_output = args.langshort
    print(args)
    if args.output_type == "both":
        for x in ["module", "overwriter"]:
            export_modules(args, x)
    elif args.output_type == "module":
        export_modules(args, "module")
    elif args.output_type == "overwriter":
        export_modules(args, "overwriter")
    else:
        warnings.warn(
            f'{args.output_type} must be "module", "overwriter", or "both" ',
            UserWarning,
        )


# TODO: 挙動が非常に不可解. 重複を削除するとかえって動かなくなる? language_data 単位でsanity checkがなされている?
# <language>/<Module Names>/<xml> のように module 毎にフォルダを分け, それぞれに language_data.xml を用意すると動くことを発見した. 不具合時の原因切り分けも多少しやすくなる
# 仕様が変なだけでなく厄介なバグもいくつかありそう
# TODO: 特殊な制御文字が結構含まれているわりにエンティティ化が必要かどうかが曖昧
# NOTE: quoteation symbols don't need to be escaped (&quot;) if quoted by another ones
# TODO: too intricate to localize


def export_modules(args: argparse.Namespace, run_type: str) -> None:
    """
    type: 'module' or 'overwriter'
    """

    # df_to_be_dropped = pd.read_csv(Path(__file__).parent.joinpath('duplications.csv'))
    df_duplication_suspected = pd.read_csv(
        Path(__file__).parent.joinpath("duplications-suspects.csv")
    )

    print(f"output type: {run_type}")
    if args.input.exists():
        if args.input.suffix == ".po":
            print(f"reading {args.input}")
            pof = polib.pofile(args.input)
        elif args.input.suffix == ".mo":
            print(f"reading {args.input}")
            pof = polib.pofile(args.input)
        else:
            raise ("input file is invalid", UserWarning)
    pof_pub = public_po(pof)
    pof_pub.save(
        args.input.parent.joinpath(args.input.with_suffix("").name + "-pub.po")
    )
    pof_pub.save_as_mofile(
        args.input.parent.joinpath(args.input.with_suffix("").name + "-pub.mo")
    )
    del pof_pub
    d = po2pddf(pof, drop_prefix_id=False)
    if not args.legacy_id:
        d = pd.concat(
            [
                d,
                d["context"]
                .str.split("/", expand=True)
                .rename(columns={0: "module", 1: "file"}),
            ],
            axis=1,
        )[["id", "text", "text_EN", "module", "file", "locations"]]
        d["duplication"] = [len(x) for x in d["locations"]]
        d["duplication"] = d["duplication"].fillna(1)
    d["module"] = d["module"].str.replace("^Hardcoded, ", "", regex=True)
    d["file"] = d["file"].str.replace("^Hardcoded, ", "", regex=True)
    d["file"] = d["file"].str.replace(f"_{args.langsuffix}.xml", ".xml")
    d.to_csv("あほしね.csv", index=False)
    if args.skip_blank_vanilla:
        d = d.loc[lambda d: d["text"] != ""]
    del pof

    if args.distinct:
        n = d.shape[0]
        d = (
            d.assign(isnative=lambda d: d["module"] == "Native")
            .sort_values(["id", "isnative"])
            .groupby(["id"])
            .last()
            .reset_index()
            .drop(columns=["isnative"])
        )
        print(f"""{n - d.shape[0]} duplicated entries dropped""")
    if "duplication" not in d.columns:
        d["duplication"] = 1
    d_duplication_entries = d.merge(
        df_duplication_suspected[["id"]], on=["id"], how="inner"
    )
    n_entries_total: int = 0
    n_change_total: int = 0
    d_used = pd.DataFrame({"id": []})
    for module in args.modules:
        if run_type == "module":
            output_dir = args.output.joinpath(
                f"CL{args.langshort}-Common/ModuleData/Languages/{args.langfolder_output}"
            ).joinpath(module)
        elif run_type == "overwriter":
            output_dir = args.output.joinpath(
                f"{module}/ModuleData/Languages/{args.langfolder_output}"
            )
        if not output_dir.exists():
            output_dir.mkdir(parents=True)
        x, y, used_id = correct_xml_in_folder_with_counting_and_writing(
            d, d_duplication_entries, module, output_dir, run_type, args
        )
        n_change_total += x
        n_entries_total += y
        d_used = pd.concat((d_used, used_id)).drop_duplicates()
    if run_type == "module" and not args.no_english_overwriting:
        lang_data_patch = generate_language_data_xml(module="", lang_id="English")
        lang_data_patch.getroot().append(
            generate_languageFile_element(
                f"{args.langfolder_output}/Native/std_global_strings_xml_{args.langsuffix}.xml"
            )
        )
        write_xml_with_default_setting(
            lang_data_patch, output_dir.joinpath("../../language_data.xml")
        )
    if run_type == "module" and args.langalias is not None:
        with args.output.joinpath(
            f"CL{args.langshort}-Common/ModuleData/Languages/{args.langfolder_output}/Native/language_data.xml"
        ) as fp:
            language_data_alias = ET.parse(fp)
        language_data = language_data_alias.find("LanguageData", recursive=False)
        language_data.attrib["id"] = args.langalias
        language_data.attrib["name"] = args.langalias
        xml_list = args.output.joinpath(
            f"CL{args.langshort}-Common/ModuleData/Languages/{args.langfolder_output}"
        ).rglob("language_data.xml")
        for fp in xml_list:
            if fp.parent != "Native":
                langauage_data2 = ET.parse(fp)
                for xml_languagefile in langauage_data2.findall("LanguageFile"):
                    language_data_alias.getroot().append(xml_languagefile)
        output_fp = args.output.joinpath(
            f"CL{args.langshort}-Common/ModuleData/Languages/{args.langfolder_output}2/language_data.xml"
        )
        if not output_fp.parent.exists():
            output_fp.parent.mkdir(parents=True)
        write_xml_with_default_setting(language_data_alias, output_fp)
    if n_entries_total > 0:
        print(
            f"""SUMMARY: {n_change_total}/{n_entries_total} ({100 * n_change_total/n_entries_total:.0f}%) text entries are changed totally"""
        )
    d_leftover = (
        d[["id", "text"]]
        .merge(d_used, on=["id"], how="outer", indicator=True)
        .loc[lambda d: d["_merge"] != "both"]
        .drop(columns=["_merge"])
        .drop_duplicates()
    )
    if not args.suppress_missing_id and not args.missing_modulewise > 0:
        write_missings(n_entries_total, d_leftover, output_dir, args)


def correct_xml_in_folder_with_counting_and_writing(
    data: pd.DataFrame,
    data_dup: pd.DataFrame,
    module_name: str,
    output_dir: Path,
    run_type: str,
    args: argparse.Namespace,
) -> Tuple[int, int, pd.DataFrame]:
    """
    モジュール(≒フォルダ)単位の置換処理をして変更箇所の数を返す. ファイルの書き込みもここで行う
    Returns:
        変更箇所の数
        確認箇所の数
        使用したIDのDF
    """
    n_changes: int = 0
    n_entries: int = 0
    base_langauge_path = (
        f"""Modules/{module_name}/ModuleData/languages/{args.langshort}"""
    )
    xml_list: List[Path] = [
        x
        for x in args.mb2dir.joinpath(base_langauge_path).glob("*.xml")
        if x.name
        not in ["language_data.xml", f"{args.langshort.lower()}_functions.xml"]
    ]

    def correct_xml_translations_with_count(
        xml: ET.ElementTree,
        data: pd.DataFrame,
        module_name: str,
        xml_path: Path,
        args: argparse.Namespace,
    ) -> Tuple[int, int, pd.DataFrame]:
        """
        指定されたXMLを修正して修正箇所の数を返す. この関数内では書き込み処理を行っていない
        Returns:
            変更箇所の数
            確認箇所の数 (つまり分母)
            一致したID
        """
        ids_matched: List[str] = []
        if xml.find("tags/tag").attrib["language"] != args.langid:
            xml.xpath("tags").append(generate_tag_element(args.langid))
        if args.langalias is not None:
            xml.xpath("tags").append(generate_tag_element(args.langalias))
        if xml.find("strings") is not None:
            n_change_xml, n_entries_xml = (0, 0)
            for string in xml.xpath("strings/string"):
                tmp = data.loc[lambda d: d["id"] == string.attrib["id"]]
                n_entries_xml += 1
                if tmp.shape[0] > 0 and tmp["text"].values[0] != "":
                    ids_matched += [string.attrib["id"]]
                    new_str = removeannoyingchars(tmp["text"].values[0])
                    if string.attrib["text"] != new_str or args.all_entries:
                        string.attrib["text"] = new_str
                        n_change_xml += 1
                else:
                    if args.legacy_id:
                        warnings.warn(
                            f"""ID not found: {string.attrib["id"]} in {module_name}/{xml_path.name}"""
                        )
                    elif args.verbose:
                        warnings.warn(
                            f"""ID not found: {string.attrib["id"]} in {module_name}/{xml_path.name}"""
                        )
                    normalized_str = removeannoyingchars(string.attrib["text"])
                    if normalized_str != string.attrib["text"]:
                        warnings.warn(
                            f"""this text could contain irregular characters (some control characters or zenkaku blanks): {string.attrib['text']}""",
                            UserWarning,
                        )
                        n_change_xml += 1
                        string.attrib["text"] = normalized_str
                    if args.distinct:
                        html.unescape((ET.tostring(string, encoding="unicode")))
                if args.with_id:
                    string.attrib["text"] = (
                        f"""[{string.attrib['id']}]{string.attrib['text']}"""
                    )
            if n_entries_xml > 0:
                print(
                    f"""{n_change_xml}/{n_entries_xml} ({100 * n_change_xml/n_entries_xml:.0f} %) text entries are changed in {xml_path.name}"""
                )
            else:
                print(f"""no translation entries in {xml_path.name}""")
        else:
            warnings.warn(f"{xml_path} is has no strings tag! processing skipped")

        return (n_change_xml, n_entries_xml, pd.DataFrame({"id": ids_matched}))

    def geneatae_en_xml_names(p: Path, args: argparse.Namespace) -> pd.Series:
        return (
            pd.Series(p.with_suffix("").name).str.replace(
                f"""{args.filename_sep}{args.langsuffix}""", ""
            )[0]
            + ".xml"
        )

    d_matched = pd.DataFrame({"id": []})
    if len(xml_list) > 0:
        if not output_dir.exists() and len(xml_list) > 0:
            output_dir.mkdir(parents=True)
        language_data = generate_language_data_xml(
            module_name, lang_id=args.langid, subtitle=args.subtitleext, iso=args.iso
        )
        for xml_path in xml_list:
            print(
                f"""Reading {xml_path.name} from {xml_path.parent.parent.parent.parent.name} Module"""
            )
            # edit language_data.xml
            xml = ET.parse(xml_path)
            en_xml_name = geneatae_en_xml_names(xml_path, args)
            # TODO: refactoring
            if args.legacy_id:
                d_sub = data.loc[
                    lambda d: (d["module"] == module_name) & (d["file"] == en_xml_name)
                ]
                if d_sub.shape[0] == 0:
                    warnings.warn(
                        f"no match entries with {en_xml_name}! subsettings skipped, which cause a bit low performance."
                    )
                    d_sub = data.loc[lambda d: (d["module"] == module_name)]
            else:
                if args.missing_modulewise:
                    d_sub = data
                else:
                    d_sub = pd.concat(
                        (data.loc[lambda d: d["file"] == en_xml_name], data_dup)
                    )
                    d_sub = d_sub[["id", "text"]].drop_duplicates()
                    if d_sub.shape[0] == 0:
                        d_sub = data
                        warnings.warn(
                            f"no match entries with {en_xml_name}! subsettings skipped, which cause a bit low performance."
                        )
                # TODO: language files get messed since v1.2.
                # ファイルごとに分けることが無意味になった. IDさえ一意ならいいので元のファイルの分け方を守る必要もなさそうだが, 正誤率を知りたいのでこうする
            if xml.getroot().tag == "base":
                n_change_xml, n_entries_xml, ids_matched = (
                    correct_xml_translations_with_count(
                        xml, d_sub, module_name, xml_path, args
                    )
                )
                d_matched = pd.concat((d_matched, ids_matched)).drop_duplicates()
                n_changes += n_change_xml
                n_entries += n_entries_xml
                language_data.getroot().append(
                    generate_languageFile_element(
                        f"{Path('/'.join([args.langfolder_output, module_name if run_type == 'module' else '', xml_path.name])).as_posix()}"
                    )
                )
                write_xml_with_default_setting(
                    xml, output_dir.joinpath(f"""{xml_path.name}""")
                )
            else:
                warnings.warn(f"{xml_path} has no base tag! processing skipped")
        write_xml_with_default_setting(
            language_data, output_dir.joinpath("language_data.xml")
        )
        if not args.suppress_missing_id and args.missing_modulewise:
            print(f"------ Checking missing IDs in {module_name} ---------")
            df_original = pd.read_excel("text/MB2BL-JP.xlsx")
            n_missings = output_missings_modulewise(
                args,
                output_dir,
                module_name,
                data.loc[lambda d: d["module"] == module_name],
                df_original,
            )
            print(f"{n_missings} missing IDs found!")
            if n_missings is not None:
                n_entries += n_missings
                n_changes += n_missings
    else:
        print(f"""No language files found inside {base_langauge_path}""")

    return (n_changes, n_entries, d_matched)


def write_missings(
    n_total: int, df_leftover: pd.DataFrame, output_dir: Path, args: argparse.Namespace
) -> None:
    """
    使われなかったエントリの出力とログ表示
    args:
        df_leftover - idカラムのみ
    """
    print("------ Checking missing IDs whole the vanilla text ---------")
    output_dir = args.output.joinpath(
        f"CL{args.langshort}-Common/ModuleData/Languages/{args.langfolder_output}"
    ).joinpath("Missings")
    if not output_dir.exists():
        output_dir.mkdir()
    language_data_missings = generate_language_data_xml(module="", lang_id=args.langid)
    language_data_missings.getroot().append(
        generate_languageFile_element(
            f"{args.langfolder_output}/Missings/str_sandbox_missings-{args.langsuffix}.xml"
        )
    )
    if df_leftover.shape[0] > 0:
        language_data_missings.getroot().append(
            generate_languageFile_element(
                f"{args.langfolder_output}/Missings/str_missings-{args.langsuffix}.xml"
            )
        )
        xml_str_missings = generate_string_xml([args.langid])
        for _, r in df_leftover.iterrows():
            new_entry = generate_new_string_element(
                r["id"], removeannoyingchars(r["text"])
            )
            xml_str_missings.find("strings").append(new_entry)
        write_xml_with_default_setting(
            xml_str_missings,
            output_dir.joinpath(f"""str_missings-{args.langsuffix}.xml"""),
        )
        write_xml_with_default_setting(
            language_data_missings, output_dir.joinpath("""language_data.xml""")
        )
    else:
        print(
            f"No missing IDs found when comparing between English and {args.langshort}"
        )
        return
    print(
        f"""SUMMARY: {df_leftover.shape[0]} entries out of {n_total}"""
        f"""({100 * (df_leftover.shape[0]/n_total):.0f}%) are missing"""
        f"""from vanilla {args.langid} language files."""
    )
    print(f"""saved to {output_dir}""")


def output_missings_modulewise(
    args: argparse.Namespace,
    output_dir: Path,
    module: str,
    df: pd.DataFrame,
    df_original: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    a
    """
    if df_original is not None:
        ids = df_original.loc[
            lambda d: (d["text_JP_original"] == "") | d["text_JP_original"].isna()
        ][["id"]]
        d_sub = df.merge(ids, on="id", how="inner")
    elif "is_missing" in df.columns:
        d_sub = df.loc[lambda d: d["id_missing"]]
    else:
        return None
    if d_sub.shape[0] < 1:
        return None
    xml = generate_string_xml([args.langid])
    strings = xml.findall("strings")
    for _, r in d_sub.iterrows():
        strings.append(
            generate_new_string_element(r["id"], removeannoyingchars(r["text"]))
        )
    write_xml_with_default_setting(
        xml, output_dir.joinpath(f"translation-missings-{args.langshort}.xml")
    )
    with output_dir.joinpath("language_data.xml") as fp:
        xml_lang_data = ET.parse(fp)
    lang_data_xml = xml_lang_data.find("LanguageData")
    new_entry = generate_languageFile_element(
        path=f"{args.langshort}/{module}/translation-missings-{args.langfolder_output}.xml"
    )
    lang_data_xml.append(new_entry)
    lang_data_xml.write(
        output_dir.joinpath("language_data.xml"),
        pretty_print=True,
        xml_declaration=True,
        encoding="utf-8",
    )
    return d_sub.shape[0]


def drop_new_duplication_error_manually(
    string: ET._Element, id_list: Iterable[str]
) -> bool:
    """
    Return: number of dropped entries
    """
    if string.attrib["id"] in id_list:
        id_ = string.attrib["id"]
        string.getparent().remove(string)
        print(f"!! duplicated ID ({id_}) dropprd")
        return True
    else:
        return False


def generate_language_data_xml(
    module: str,
    lang_id: str,
    name: Optional[str] = None,
    subtitle: Optional[str] = None,
    iso: Optional[str] = None,
    dev: str = "false",
) -> ET.ElementTree:
    """
    a
    """
    language_data = ET.fromstring(
        """
        <LanguageData>
        </LanguageData>
        """
    )
    language_data.set("id", lang_id)
    if module == "Native":
        language_data.set("name", lang_id if name is None else name)
    if subtitle is not None:
        language_data.set("subtitle_extension", subtitle)
    if iso is not None:
        language_data.set("supported_iso", iso)
    language_data.set("under_development", dev)
    return ET.ElementTree(language_data)


def generate_string_xml(langids: List[str]) -> ET.ElementTree:
    """
    a
    """
    xml = ET.fromstring(
        """
        <base>
        <tags></tags>
        <strings></strings>
        </base>
        """
    )
    _ = [xml.find("tags").append(ET.fromstring(f'<tag id="{id}" />')) for id in langids]
    return ET.ElementTree(xml)


def generate_tag_element(lang_id: str) -> ET.ElementTree:
    """
    a
    """
    return ET.fromstring(f'<tag language="{lang_id}" />')


def generate_languageFile_element(path: str) -> ET.ElementTree:
    """
    a
    """
    return ET.fromstring(f'<LanguageFile xml_path="{path}" />')


def generate_new_string_element(loc_id: str, text: str):
    """
    a
    """
    new_entry = ET.fromstring("""<string id="PLAHECOLHDER" text="[PLACEHOLDER]" />""")
    new_entry.attrib["id"] = loc_id
    new_entry.attrib["text"] = text
    return new_entry


def write_xml_with_default_setting(xml: ET.ElementTree, fpath: Path) -> bool:
    """
    a
    """
    ET.indent(xml, space="  ", level=0)
    xml.write(fpath, pretty_print=True, xml_declaration=True, encoding="utf-8")
    return True


if __name__ == "__main__":
    main()
