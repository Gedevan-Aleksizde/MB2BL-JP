#!/usr/bin/env python3
"""Read vanilla ModuleData and language catalogs, preserving exact-msgid translations."""

import argparse
import csv
import io
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import polib
import yaml
from functions import FILTERS, initializePOFile
from lxml import etree as ET

MODULES = [
    "Native",
    "SandBox",
    "SandBoxCore",
    "CustomBattle",
    "MultiPlayer",
    "StoryMode",
    "FastMode",
    "BirthAndDeath",
]
GAME_DIR = Path(
    "C:/Program Files (x86)/Steam/steamapps/common/Mount & Blade II Bannerlord"
)
MARKER = re.compile(r"^\{=([^}]+)\}(.*)$", re.S)
INVISIBLE = re.compile("[\u00a0\u180e\u2007\u200b\u200f\u202f\u2060\ufeff]")


@dataclass(frozen=True)
class Record:
    id: str
    text: str
    module: str
    file: str
    attribute: str
    line: int


def defaults():
    path = Path(__file__).with_name("default.yml")
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}


def parse_xml(path):
    """Honor XML encodings; handle the game's incorrectly declared UTF-8 files."""
    try:
        return ET.parse(str(path))
    except ET.XMLSyntaxError:
        text = path.read_text(encoding="utf-8-sig")
        text = re.sub(
            r"(<\?xml[^?]*encoding\s*=\s*)[\x22\x27][^\x22\x27]*[\x22\x27]",
            r'\1"utf-8"',
            text,
            count=1,
        )
        return ET.ElementTree(ET.fromstring(text.encode("utf-8")))


def sorted_xmls(directory):
    return sorted(
        directory.rglob("*.xml"),
        key=lambda p: p.relative_to(directory).as_posix().casefold(),
    )


def source_records(module, module_dir, modules_dir):
    records = []
    for path in sorted_xmls(module_dir / "ModuleData"):
        if path.relative_to(module_dir / "ModuleData").parts[0].lower() == "languages":
            continue
        document = parse_xml(path)
        # Rules overlap (notably string.text). Visit each physical attribute once,
        # in document order rather than FILTERS order.
        selected = set()
        for rule in FILTERS:
            for element in document.xpath(rule["xpath"]):
                if rule["key"] not in element.attrib:
                    raise ValueError(
                        f"{path}:{element.sourceline}: missing attribute {rule['key']}"
                    )
                selected.add((element, rule["key"]))
        for element in document.iter():
            for attribute, value in element.attrib.items():
                if (element, attribute) not in selected:
                    continue
                match = MARKER.match(value)
                if match:
                    records.append(
                        Record(
                            match[1],
                            match[2],
                            module,
                            path.relative_to(modules_dir).as_posix(),
                            f"{module}.{ET.QName(element).localname}.{attribute}",
                            element.sourceline or 0,
                        )
                    )
    return records


def language_records(module, module_dir, modules_dir, langshort, langid):
    directory = module_dir / "ModuleData/Languages"
    documents = {}

    def document(path):
        path = path.resolve()
        if path not in documents:
            documents[path] = parse_xml(path)
        return documents[path]

    target_files = []
    english_files = []
    for path in sorted_xmls(directory):
        relative = path.relative_to(directory)
        if path.name.lower().endswith("_functions.xml"):
            continue
        tree = document(path)
        if path.name.lower() == "language_data.xml":
            if tree.getroot().get("id") == langid:
                for reference in tree.findall("./LanguageFile"):
                    candidate = (
                        directory / reference.attrib["xml_path"].replace("\\", "/")
                    ).resolve()
                    if not candidate.is_relative_to(directory.resolve()):
                        raise ValueError(
                            f"Language reference outside {directory}: {candidate}"
                        )
                    if not candidate.name.lower().endswith("_functions.xml"):
                        if not candidate.is_file():
                            raise FileNotFoundError(candidate)
                        target_files.append(candidate)
            continue
        in_english_folder = len(relative.parts) == 1 or (
            len(relative.parts) == 2 and relative.parts[0].lower() == "en"
        )
        english_tag = any(
            e.get("language") == "English" for e in tree.findall("./tags/tag")
        )
        if in_english_folder or english_tag:
            english_files.append(path.resolve())
    if module.lower() == "native":
        target_files.extend(
            p.resolve() for p in sorted_xmls(directory / langshort / "NoTranslation")
        )

    def read(paths):
        result = []
        for path in dict.fromkeys(paths):
            for element in document(path).findall("./strings/string"):
                result.append(
                    Record(
                        element.attrib["id"],
                        element.attrib["text"],
                        module,
                        path.relative_to(modules_dir.resolve()).as_posix(),
                        f"{module}.language.text",
                        element.sourceline or 0,
                    )
                )
        return result

    return read(english_files), read(target_files)


def group_records(records):
    groups = {}
    for record in records:
        groups.setdefault(record.id, []).append(record)
    return groups


def csv_text(rows, fields):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return "\ufeff" + stream.getvalue()


def records_csv(records):
    return csv_text([asdict(r) for r in records], list(Record.__dataclass_fields__))


def escaped(text):
    return INVISIBLE.sub("", text).replace("%", "%%")


def build_catalog(
    sources, english, target, locale, old=None, all_fuzzy=False, only_diff=False
):
    groups = [group_records(records) for records in (sources, english, target)]
    old_entries = (
        {} if old is None else {e.msgid: e for e in reversed(old) if not e.obsolete}
    )
    catalog = initializePOFile(locale)
    catalog.wrapwidth = 0
    if old is not None:
        catalog.metadata.update(old.metadata)
        catalog.metadata["Language"] = locale
    for identifier in sorted(set().union(*(set(g) for g in groups))):
        records = [g.get(identifier, []) for g in groups]
        representative = next(rows[0] for rows in records if rows)
        # Source XML > English catalog > target-language-only fallback.
        msgid = identifier + "/" + escaped(representative.text)
        translation = escaped(records[2][0].text) if records[2] else ""
        entry = polib.POEntry(
            msgid=msgid,
            msgstr="" if only_diff else translation,
            msgctxt=representative.attribute,
            flags=["fuzzy"],
        )
        entry.occurrences = list(
            dict.fromkeys((r.file, str(r.line)) for rows in records for r in rows)
        )
        previous = old_entries.get(msgid)
        if previous is not None:
            entry.msgstr = previous.msgstr
            entry.flags = list(previous.flags)
            entry.comment = previous.comment
            entry.tcomment = previous.tcomment
        if not records[0] and "HARDCODED" not in entry.tcomment.splitlines():
            entry.tcomment = "\n".join(filter(None, [entry.tcomment, "HARDCODED"]))
        if all_fuzzy and "fuzzy" not in entry.flags:
            entry.flags.append("fuzzy")
        catalog.append(entry)
    current = {e.msgid for e in catalog}
    dropped = [] if old is None else [e for e in old if e.msgid not in current]
    return catalog, dropped


def write_outputs(outputs, timestamp):
    """Stage every output before moving existing files to timestamped backups."""
    backups = {
        p: p.with_name(f"{p.stem}-{timestamp}{p.suffix}") for p in outputs if p.exists()
    }
    for backup in backups.values():
        if backup.exists():
            raise FileExistsError(f"Backup already exists: {backup}")
    staged = {}
    try:
        for path, text in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                dir=path.parent, suffix=".tmp", delete=False
            ) as stream:
                staged[path] = Path(stream.name)
                stream.write(text.encode("utf-8"))
        for path, temporary in staged.items():
            if path in backups:
                path.rename(backups[path])
            os.replace(temporary, path)
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)


def main(argv=None):
    config = defaults()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mb2dir", type=Path, default=Path(config.get("mb2dir", GAME_DIR))
    )
    parser.add_argument(
        "--vanilla_modules", "--vanilla-modules", nargs="+", default=MODULES
    )
    parser.add_argument("--langshort", default=config.get("langshort", "JP"))
    parser.add_argument("--langid", default=None)
    parser.add_argument("--locale", default=None)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pofile", type=Path)
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--all-fuzzy", action="store_true")
    parser.add_argument("--only-diff", action="store_true")
    args = parser.parse_args(argv)
    timestamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    if args.langid is None:
        args.langid = (
            config.get("langid", "日本語")
            if args.langshort == config.get("langshort", "JP")
            else args.langshort
        )
    locale = args.locale or (
        config.get("locale", "ja_JP") if args.langshort == "JP" else args.langshort
    )
    output = args.output or Path(f"text/MB2BL-{args.langshort}.po")
    report_dir = args.report_dir or output.parent
    modules_dir = (args.mb2dir / "Modules").resolve()
    sources, english, target = [], [], []
    try:
        for module in args.vanilla_modules:
            if Path(module).name != module or module in (".", ".."):
                raise ValueError(f"Invalid module folder: {module}")
            module_dir = modules_dir / module
            if not (module_dir / "ModuleData").is_dir():
                raise FileNotFoundError(module_dir / "ModuleData")
            sources.extend(source_records(module, module_dir, modules_dir))
            en, translated = language_records(
                module, module_dir, modules_dir, args.langshort, args.langid
            )
            english.extend(en)
            target.extend(translated)
        no_id = [
            r for rows in (sources, english, target) for r in rows if r.id in ("!", "*")
        ]
        sources, english, target = [
            [r for r in rows if r.id not in ("!", "*")]
            for rows in (sources, english, target)
        ]
        old_path = args.pofile or output
        old = (
            polib.pofile(str(old_path), encoding="utf-8-sig")
            if old_path.exists()
            else None
        )
        catalog, dropped = build_catalog(
            sources, english, target, locale, old, args.all_fuzzy, args.only_diff
        )
        reports = {"no-id.csv": records_csv(no_id)}
        target_report = (
            f"duplications-{args.langshort}.csv"
            if args.langshort.upper() != "EN"
            else "duplications-target-EN.csv"
        )
        for name, records in [
            ("duplications.csv", sources),
            ("duplications-EN.csv", english),
            (target_report, target),
        ]:
            reports[name] = records_csv(
                [
                    r
                    for rows in group_records(records).values()
                    if len(rows) > 1
                    for r in rows
                ]
            )
        reports["dropped.csv"] = csv_text(
            [
                {
                    "msgid": e.msgid,
                    "msgstr": e.msgstr,
                    "context": e.msgctxt or "",
                    "flags": json.dumps(e.flags),
                    "comment": e.comment,
                    "translator_comment": e.tcomment,
                    "occurrences": json.dumps(e.occurrences, ensure_ascii=False),
                }
                for e in dropped
            ],
            [
                "msgid",
                "msgstr",
                "context",
                "flags",
                "comment",
                "translator_comment",
                "occurrences",
            ],
        )
        write_outputs(
            {
                **{report_dir / name: text for name, text in reports.items()},
                output: str(catalog),
            },
            timestamp,
        )
        print(
            f"Wrote {len(catalog)} entries to {output}; {len(dropped)} dropped; {len(no_id)} special-ID occurrences"
        )
    except (OSError, ValueError, ET.XMLSyntaxError) as error:
        parser.exit(1, f"Error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
