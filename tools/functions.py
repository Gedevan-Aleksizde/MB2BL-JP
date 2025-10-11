#! /usr/bin/env python3
# encoding: utf-8
import argparse
import copy
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, TypedDict

import numpy as np
import pandas as pd
import polib
import regex
import yaml


class dict_name_attr(TypedDict):
    context: str
    key: str
    xpath: str
    xml_name_id: str


FILTERS: List[dict_name_attr] = [
    dict(
        context="Concept.title",
        xpath=".//Concept[@title][@id]",
        key="title",
        xml_name_id="Concepts",
    ),
    dict(
        context="Concept.description",
        xpath=".//Concept[@description][@id]",
        key="description",
        xml_name_id="Concepts",
    ),
    dict(
        context="Culture.name",
        xpath=".//Culture[@name][@id]",
        key="name",
        xml_name_id="Cultures",
    ),
    dict(
        context="Culture.text",
        xpath=".//Culture[@text][@id]",
        key="text",
        xml_name_id="Cultures",
    ),
    dict(
        context="Culture.femaleName",
        xpath=".//female_names/name[@name]",
        key="name",
        xml_name_id="Cultures",
    ),
    dict(
        context="Culture.maleName",
        xpath=".//male_names//name[@name]",
        key="name",
        xml_name_id="Cultures",
    ),
    dict(
        context="Culture.clanName",
        xpath=".//clan_names/name[@name]",
        key="name",
        xml_name_id="Cultures",
    ),
    dict(
        context="CraftedItem.name",
        xpath=".//CraftedItem[@name][@id]",
        key="name",
        xml_name_id="Cultures",
    ),
    dict(
        context="CraftingPiece.name",
        xpath=".//CraftingPiece[@name][@id]",
        key="name",
        xml_name_id="CraftingPieces",
    ),
    dict(
        context="Faction.name",
        xpath=".//Faction[@name][@id]",
        key="name",
        xml_name_id="Factions",
    ),
    dict(
        context="Faction.short_name",
        xpath=".//Faction[@short_name][@id]",
        key="short_name",
        xml_name_id="Factions",
    ),
    dict(
        context="Faction.text",
        xpath=".//Faction[@text][@id]",
        key="text",
        xml_name_id="Factions",
    ),
    dict(
        context="Kingdom.name",
        xpath=".//Kingdom[@name][@id]",
        key="name",
        xml_name_id="Kingdoms",
    ),
    dict(
        context="Kingdom.short_name",
        xpath=".//Kingdom[@short_name][@id]",
        key="short_name",
        xml_name_id="Kingdoms",
    ),
    dict(
        context="Kingdom.text",
        xpath=".//Kingdom[@text][@id][@id]",
        key="text",
        xml_name_id="Kingdoms",
    ),
    dict(
        context="Kingdom.title",
        xpath=".//Kingdom[@title][@id]",
        key="title",
        xml_name_id="Kingdoms",
    ),
    dict(
        context="Kingdom.ruler_title",
        xpath=".//Kingdom[@ruler_title][@id]",
        key="ruler_title",
        xml_name_id="Kingdoms",
    ),
    dict(
        context="Hero.text",
        xpath=".//Hero[@text][@id]",
        key="text",
        xml_name_id="Heroes",
    ),
    dict(
        context="Item.name",
        xpath=".//Item[@name][@id]",
        key="name",
        xml_name_id="Items",
    ),
    dict(
        context="ItemModifier.name",
        xpath=".//ItemModifier[@name][@id]",
        key="name",
        xml_name_id="ItemModifiers",
    ),
    dict(
        context="NPCCharacter.name",
        xpath=".//NPCCharacter[@name][@id]",
        key="name",
        xml_name_id="NPCCharacters",
    ),
    dict(
        context="NPCCharacter.text",
        xpath=".//NPCCharacter[@text][@id]",
        key="text",
        xml_name_id="NPCCharacters",
    ),
    dict(
        context="Module_String.string",
        xpath=".//string[@text][@id]",
        key="text",
        xml_name_id="GameText",
    ),
    dict(
        context="Settlement.name",
        xpath=".//Settlement[@name][@id]",
        key="name",
        xml_name_id="Settlements",
    ),
    dict(
        context="Settlement.text",
        xpath=".//Settlement[@text][@id]",
        key="text",
        xml_name_id="Settlements",
    ),
    dict(
        context="SiegeEngineType.name",
        xpath=".//SiegeEngineType[@name][@id]",
        key="name",
        xml_name_id="",
    ),
    dict(
        context="SiegeEngineType.description",
        xpath=".//SiegeEngineType[@description][@id]",
        key="description",
        xml_name_id="",
    ),
    dict(context="Scene.name", xpath=".//Scene[@name]", key="name", xml_name_id=""),
    dict(context="Area.name", xpath=".//Area[@name]", key="name", xml_name_id=""),
    # Shokuho
    dict(
        context="Religion.fullName",
        xpath=".//Religion[@fullName]",
        key="fullName",
        xml_name_id="",
    ),
    dict(
        context="Religion.adjective",
        xpath=".//Religion[@adjective]",
        key="adjective",
        xml_name_id="",
    ),
    # 以下はBanner Kings独自実装のスキーマ
    dict(
        context="duchy.name", xpath=".//duchy[@name][@id]", key="name", xml_name_id=""
    ),
    dict(
        context="duchy.fullName",
        xpath=".//duchy[@fullName][@id]",
        key="fullName",
        xml_name_id="",
    ),
    dict(
        context="WorkshopType.name",
        xpath=".//WorkshopType[@name][@id]",
        key="name",
        xml_name_id="",
    ),
    dict(
        context="WorkshopType.jobname",
        xpath=".//WorkshopType[@jobname][@id]",
        key="jobname",
        xml_name_id="",
    ),
    dict(
        context="WorkshopType",
        xpath=".//WorkshopType[@description][@id]",
        key="description",
        xml_name_id="",
    ),
    dict(
        context="string.title",
        xpath=".//string[@title][@id]",
        key="title",
        xml_name_id="",
    ),
    dict(
        context="Project.name",
        xpath=".//Project[@name][@id]",
        key="name",
        xml_name_id="",
    ),
    # for Improved Minor Factions
    dict(
        context="IMFText.text",
        xpath=".//IMFText[@text]",
        key="text",
        xml_name_id="",
    ),
    dict(
        context="string.text", xpath=".//string[@text][@id]", key="text", xml_name_id=""
    ),
    # TODO: Custom Spawn API
    dict(
        context="NameSignifier.value",
        xpath=".//NameSignifier[@value]",
        key="value",
        xml_name_id="",
    ),
    # TODO: RegularBanditDailySpawnData -> Name, SpawnMessage, DeathMessage
    # for Shokuho
    dict(
        context="Book.desc",
        xpath=".//Book[@desc]",
        key="desc",
        xml_name_id="",
    ),
]


control_char_remove = regex.compile(r"\p{C}")
match_public_id_legacy = regex.compile(r"^(.+?/.+?/.+?)/.*$")
match_file_name_id_legacy = regex.compile(r"^.+?/(.+?)/.+?/.*$")
match_internal_id_legacy = regex.compile(r"^.+?/.+?/(.+?)/.*$")
match_prefix_id = regex.compile(r"^\[.+?\](.*)$")

match_public_id = regex.compile(r"^(.+?)/.+$")
match_string = regex.compile(r"^.+?/(.+)$")


def merge_yml(
    fp: Path, args: argparse.Namespace, default: argparse.Namespace
) -> argparse.Namespace:
    with fp.open("r", encoding="utf-8") as f:
        yml = yaml.load(f, Loader=yaml.Loader)
        for k in yml.keys():
            if yml[k] == "None":
                yml[k] = None
            if (
                k in ["outdir", "mb2dir", "mo2dir", "merge_with_gettext"]
                and yml[k] is not None
            ):
                yml[k] = Path(yml[k])
    d_args = vars(args)
    d_default = vars(default)
    d_args_updated = {k: v for k, v in d_args.items() if v is not None}
    d_args_extra = {k: v for k, v in d_default.items() if k not in yml.keys()}
    yml.update(d_args_extra)
    yml.update(d_args_updated)
    d_args = yml
    args = argparse.Namespace(**d_args)
    if args.filename_sep_version is None:
        args.filename_sep_version = "1.2"
    if args.filename_sep_version not in ["1.0", "1.1", "1.2"]:
        warnings.warn("The value for --filename-sep-version is irregular! set to `1.2`")
        args.filename_sep_version = "1.2"
    args.filename_sep = "_" if args.filename_sep_version == "1.2" else "-"
    return args


def public_po(pofile: polib.POFile) -> polib.POFile:
    # TODO: copy of metadata
    # TODO: distinction
    pofile = copy.deepcopy(pofile)
    for entry in pofile:
        entry.msgid = match_public_id.sub(r"\1", entry.msgid)
    return pofile


def po2pddf(
    pofile: polib.POFile,
    drop_prefix_id: bool = True,
    drop_excessive_cols: bool = True,
    legacy: bool = False,
) -> pd.DataFrame:
    """
    input:
    return: `pandas.DataFrame` which contains `id`, `file`, `module`, `text`, `text_EN ,`notes`, `flags` columns
    """
    d = pd.DataFrame(
        [
            (x.msgid, x.msgstr, x.tcomment, x.flags, x.occurrences, x.msgctxt)
            for x in pofile
            if x.msgid != ""
        ],
        columns=["id", "text", "notes", "flags", "locations", "context"],
    )
    d = pd.concat([d, d["id"].str.split("/", expand=True)], axis=1).drop(columns="id")
    if legacy:
        d = d.rename(columns={0: "module", 1: "file", 2: "id"})
        d["context"] = d["file"]
    else:
        d = d.rename(columns={0: "id"})
        d = d.rename(columns={1: "text_EN"})
        d = d.assign(duplication=lambda d: [len(x) for x in d["locations"]])
        d["text_EN"] = d["text_EN"].str.replace("%%", "%")
    d["text"] = d["text"].str.replace("%%", "%")
    d["id"] = d["id"].str.replace("%%", "%")
    if drop_prefix_id:
        d["text"] = [match_prefix_id.sub(r"\1", x) for x in d["text"]]
    if drop_excessive_cols:
        d = d[
            [
                x
                for x in d.columns
                if x
                in [
                    "id",
                    "text",
                    "text_EN",
                    "notes",
                    "flags",
                    "locations",
                    "context",
                    "file",
                    "module",
                    "duplication",
                ]
            ]
        ]
    return d


def po2pddf_easy(pofile: polib.POFile, with_id=False) -> pd.DataFrame:
    """
    input:
    return: `pandas.DataFrame` which contains `id` and `text` columns
    """
    d = pd.DataFrame(
        [(x.msgid, x.msgstr, " ".join(x.tcomment)) for x in pofile if x.msgid != ""],
        columns=["id", "text", "note"],
    )
    internal_id = regex.compile("(^.+?)/(.+?)$")
    d["text"] = d["text"].str.replace("%%", "%")
    d["id"] = d["id"].str.replace("%%", "%")
    d["id"] = [internal_id.sub(r"\1", x) for x in d["id"]]
    if with_id:
        d["text"] = "[" + d["id"] + "]" + d["text"]
    return d


def initializePOFile(
    lang: str, encoding: str = "utf-8", email: Optional[str] = None
) -> polib.POFile:
    po = polib.POFile(encoding=encoding)
    dt = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S%z")
    metadata = {
        "Project-Id-Version": "1.0",
        "POT-Creation-Date": dt,
        "PO-Revision-Date": dt,
        "MIME-Version": "1.0",
        "Language": lang,
        "Content-Type": "text/plain; charset=utf-8",
        "Plural-Forms": "nplurals=1; plural=0;",
        "Genereted-BY": "polib",
        "Content-Transfer-Encoding": "8bit",
    }
    if email:
        metadata["Last-Translator"] = email
        metadata["Report-Msgid-Bugs-To"] = email
        metadata["Language-Team"] = f"""{lang}, {email}"""
    po.metadata = metadata
    return po


def pddf2po(
    df: pd.DataFrame,
    with_id: bool = True,
    make_distinct: bool = True,
    regacy_mode: bool = False,
    locale: str = None,
    col_id_text: str = "text",
    col_text: str = "text",
    col_locations: str = None,
    col_context: str = None,
    col_comments: str = None,
    col_flags: str = None,
) -> polib.POFile:
    """
    input: `pandas.DataFrame` which contains `id` and `text` columns
    """
    if locale is None:
        locale = "ja_JP"
    if make_distinct:
        df_unique = df.groupby("id").last().reset_index()
        if df.shape[0] != df_unique.shape[0]:
            warnings.warn(
                f"{df.shape[0] - df_unique.shape[0]} duplicated IDs are dropped!",
                UserWarning,
            )
    else:
        df_unique = df
    del df
    df_unique[col_text] = np.where(
        df_unique[col_text].isna() | df_unique[col_text].isnull(),
        "",
        df_unique[col_text],
    )
    pof = initializePOFile(lang="ja_JP")
    if with_id:
        df_unique[col_text] = [
            f'[{r["id"]}]{r[col_text]}' for _, r in df_unique.iterrows()
        ]
    print(f"col_flags={col_flags}, {col_flags is None}")

    if not regacy_mode:

        def format_arg(dic: dict) -> dict:
            dic["msgid"] = f"""{dic['id']}/{dic[col_id_text]}"""
            dic["msgstr"] = dic[col_text]
            if col_flags is None:
                dic["flags"] = ["fuzzy"]
            else:
                dic["flags"] = dic.get(col_flags)
            if col_locations is not None:
                dic["occurrences"] = [(str(x), 0) for x in dic.get(col_locations)]
            dic["tcomment"] = (
                dic.get(col_comments, "")
                if type(dic.get(col_comments, "")) is list
                else []
            )
            dic["msgctxt"] = dic.get(col_context)
            return dic

    else:

        def format_arg(dic: dict) -> dict:
            dic["msgid"] = f"""{dic['id']}/{dic[col_id_text]}"""
            dic["msgstr"] = dic[col_text]
            if col_flags is None:
                pass
            else:
                dic["flags"] = [] if dic.get("updated") else ["fuzzy"]
            dic["occurrences"] = [(dic.get(col_locations), 0)]
            dic["tcomment"] = [dic.get(col_comments, "")]
            dic["msgctxt"] = dic.get(col_context)
            return dic

    d = [format_arg(dict(r)) for _, r in df_unique.iterrows()]
    keys = {"msgid", "msgstr", "flags"}
    if col_comments is not None:
        keys.add("tcomment")
    if col_context is not None:
        keys.add("msgctxt")
    if col_locations is not None:
        keys.add("occurrences")
    current_keys = list(d[0].keys())
    _ = [dic.pop(k, None) for dic in d for k in current_keys if k not in keys]
    for r in d:
        pof.append(polib.POEntry(**r))
    return pof


def removeannoyingchars(string: str, remove_id=False) -> str:
    # TODO: against potential abusing of control characters
    string = string.replace("\u3000", " ")  # why dare you use zenkaku blank??
    string = control_char_remove.sub("", string)
    if remove_id:
        string = regex.sub(r"^\[.+?\](.*)$", r"\1", string)
    return string


def update_with_older_po(
    old_po: polib.POFile,
    new_po: polib.POFile,
    all_fuzzy=False,
    ignore_facial=True,
    legacy_id=False,
) -> polib.POFile:
    if legacy_id:
        for entry in new_po:
            if entry.msgid != "":
                old_entry = old_po.find(entry.msgid)
                if old_entry is not None:
                    old_entry.msgstr = match_public_id_legacy.sub(
                        r"\1", old_entry.msgstr
                    )
                    if old_entry.msgstr != "":
                        new_entry = new_po.find(entry.msgid)
                        if new_entry is not None:
                            new_entry.msgstr = old_entry.msgstr
                            new_entry.tcomment = old_entry.tcomment
                else:
                    print(f"error: irregular catlog ID={entry.msgid}")
        # update on public id if not matched
        old_po_fuzzy = initializePOFile("ja_JP")
        for entry in old_po:
            old_po_fuzzy.append(
                polib.POEntry(
                    msgid=match_public_id_legacy.sub(r"\1", entry.msgid),
                    msgstr=entry.msgstr,
                    tcomment=entry.tcomment,
                    flags=entry.flags,
                    msgctxt=entry.msgctxt,
                    occurrences=entry.occurrences,
                )
            )
        n_match = 0
        for entry in new_po:
            if entry.msgid != "":
                old_entry = old_po_fuzzy.find(
                    match_public_id_legacy.sub(r"\1", entry.msgid)
                )
                if old_entry is not None and old_po.find(entry.msgid) is None:
                    n_match += 1
                    new_entry = new_entry.find(entry.msgid)
                    if new_entry is not None:
                        new_entry.msgstr = old_entry.msgstr
                        new_entry.tcomment += old_entry.tcomment
                        new_entry.flags = (
                            ["fuzzy"] if all_fuzzy or "fuzzy" in old_entry.flags else []
                        )
        print(f"Updated {n_match} entries matched on public ID")
    else:
        suffix_facial = regex.compile(r"(\[ib:.+\]|\[if:.+\])")  # against v1.2 updates
        n_match = 0
        for entry in new_po:
            if entry.msgid != "":
                old_entry = (
                    old_po.find(suffix_facial.sub("", entry.msgid))
                    if ignore_facial
                    else old_po.find(entry.msgid)
                )
                if old_entry is not None:
                    if old_entry.msgstr != "":
                        new_entry = new_po.find(entry.msgid)
                        if new_entry is not None:
                            new_entry.msgstr = old_entry.msgstr
                            new_entry.tcomment += old_entry.tcomment
                            new_entry.flags = (
                                ["fuzzy"]
                                if all_fuzzy or "fuzzy" in old_entry.flags
                                else []
                            )
                            new_entry.fuzzy = (
                                True
                                if all_fuzzy or "fuzzy" in old_entry.flags
                                else False
                            )
                            new_entry.msgctxt = old_entry.msgctxt
                            n_match += 1
        total_entries = len([m for m in new_po if m.msgid != ""])
        print(
            f"Updated {n_match}/{total_entries} entries matched by both the internal ID"
        )
        if n_match == total_entries:
            print("all entries are matched")
        else:
            # update on public ID if the original text changed or somewhat get hardcoded
            old_po_fuzzy = initializePOFile("ja_JP")
            for entry in old_po:
                old_po_fuzzy.append(
                    polib.POEntry(
                        msgid=match_public_id.sub(r"\1", entry.msgid),
                        msgstr=entry.msgstr,
                        tcomment=entry.tcomment,
                        flags=(
                            set(entry.flags) | set("fuzzy")
                            if all_fuzzy or "fuzzy" in entry.flags
                            else list()
                        ),
                        msgctxt=entry.msgctxt,
                    )
                )
            n_match = 0
            for entry in new_po:
                if entry.msgid != "":
                    old_entry = old_po_fuzzy.find(
                        match_public_id.sub(r"\1", entry.msgid)
                    )
                    if (
                        old_entry is not None
                        and old_entry.msgstr != ""
                        and old_po.find(entry.msgid) is None
                        and old_entry.msgstr != entry.msgstr
                    ):
                        new_entry = new_po.find(entry.msgid)
                        if new_entry is not None:
                            new_entry.msgstr = old_entry.msgstr
                            new_entry.tcomment += old_entry.tcomment
                            new_entry.flags = ["fuzzy"]
                            new_entry.fuzzy = True
                            new_entry.msgctxt = old_entry.msgctxt
                            n_match += 1
            print(f"Updated {n_match} entries matched by the public ID")
    return new_po


def export_id_text_list(fpath: Path, output: Path) -> None:
    """
    read pofile and export as csv with id and text columns. mainly used for compare with misassigned IDs in the third-party mods
    """
    pof = polib.pofile(fpath, encoding="utf-8")
    d = pd.DataFrame([(x.msgid) for x in pof if x.msgid != ""], columns=["id"])
    d["text_EN"] = d["id"].str.replace(r"^(.+?)/(.+?)$", r"\2", regex=True)
    d["id"] = d["id"].str.replace(r"^(.+?)/.+?$", r"\1", regex=True)
    if output.exists():
        backup_path = output.parent.joinpath(
            f"""vanilla-id-{datetime.now().strftime("%Y-%m-%dT%H%M%S")}.csv"""
        )
        print(f"{output} already exists. the older file is moved to {backup_path}")
        output.rename(backup_path)
    d.to_csv(output, index=False)
