#!/usr/bin/env python3
"""Export vanilla PO translations as MODULE/TAG.ATTRIBUTE-jp.xml catalogs."""
import argparse
from collections import defaultdict
from pathlib import Path

from lxml import etree as ET
import polib

from functions import removeannoyingchars
from read_vanilla_XML import GAME_DIR, MODULES, defaults, language_records


def language_data(langid, files, subtitle='jp', iso=None):
    root = ET.Element('LanguageData', id=langid, name=langid,
                      subtitle_extension=subtitle, under_development='false')
    if iso:
        root.set('supported_iso', iso)
    for path in files:
        ET.SubElement(root, 'LanguageFile', xml_path=path)
    return root


def strings_xml(langid, entries, alias=None):
    root = ET.Element('base', type='string')
    ET.SubElement(ET.SubElement(root, 'tags'), 'tag', language=langid)
    if alias:
        ET.SubElement(root.find('tags'), 'tag', language=alias)
    strings = ET.SubElement(root, 'strings')
    for identifier, text in entries:
        ET.SubElement(strings, 'string', id=identifier, text=text)
    return root


def xml_bytes(root):
    return ET.tostring(root, pretty_print=True, xml_declaration=True, encoding='utf-8')


def context_parts(entry):
    context = entry.msgctxt or ''
    parts = context.split('.', 2)
    if len(parts) == 3 and all(parts):
        module, tag, attribute = parts
    else:
        # Old PO files remain exportable until they have been reimported.
        location = context if '/' in context else next((p for p, _ in entry.occurrences), '')
        module = location.replace('Hardcoded, ', '').replace('\\', '/').split('/')[0]
        tag, attribute = 'language', 'text'
    for part in (module, tag, attribute):
        if not part or part in ('.', '..') or any(c in part for c in '/\\:'):
            raise ValueError(f'Invalid or missing context for {entry.msgid}: {context!r}')
    return module, tag, attribute


def load_vanilla_translations(args):
    """Read export baselines and the first Japanese translation for each ID."""
    original = {}
    japanese = {}
    modules_dir = (args.mb2dir / 'Modules').resolve()
    for module in dict.fromkeys([*MODULES, *args.modules]):
        module_dir = modules_dir / module
        if not (module_dir / 'ModuleData').is_dir():
            continue
        _, jp_entries = language_records(
            module, module_dir, modules_dir, 'JP', '日本語'
        )
        for record in jp_entries:
            japanese.setdefault(record.id, record.text)
        if not args.all_entries and module in args.modules:
            if args.langshort == 'JP' and args.langid == '日本語':
                entries = jp_entries
            else:
                _, entries = language_records(
                    module, module_dir, modules_dir, args.langshort, args.langid
                )
            for record in entries:
                original.setdefault((module, record.id), record.text)
    return original, japanese


def report_correction_rate(catalog, japanese):
    """Compare all PO entries, before any export filtering or text cleanup."""
    total = len(catalog)
    missing = 0
    different = 0
    for entry in catalog:
        identifier = entry.msgid.partition('/')[0]
        if identifier not in japanese:
            missing += 1
            different += 1
        elif entry.msgstr.replace('%%', '%') != japanese[identifier]:
            different += 1
    rate = different / total * 100 if total else 0.0
    print(
        f'翻訳修正率: {different}/{total}件 ({rate:.2f}%) が本体の日本語と不一致'
        f' (うち本体にIDなし: {missing}件、不一致に含む)'
    )
    return different, total, missing


def export_catalog(args, run_type, *, catalog=None, original=None):
    if catalog is None:
        catalog = polib.pofile(str(args.input), encoding='utf-8-sig')
    if original is None:
        original, _ = load_vanilla_translations(args)
    grouped = defaultdict(list)
    global_overrides = []
    seen = set()
    for entry in catalog:
        if entry.obsolete:
            continue
        identifier, separator, _ = entry.msgid.partition('/')
        if not separator:
            raise ValueError(f'Expected ID/original msgid: {entry.msgid}')
        if identifier in ('!', '*'):
            continue
        if not entry.msgstr and args.skip_blank_vanilla:
            continue
        module, tag, attribute = context_parts(entry)
        if module not in args.modules:
            continue
        if identifier in seen:
            raise ValueError(f'Duplicate localization ID: {identifier}; reimport the PO first')
        seen.add(identifier)
        text = removeannoyingchars(entry.msgstr.replace('%%', '%'))
        if not args.all_entries and original.get((module, identifier)) == text:
            continue
        if args.with_id:
            text = f'[{identifier}]' + text
        grouped[(module, tag, attribute)].append((identifier, text))
        if module == 'Native' and any('std_global_strings' in Path(p.replace('\\', '/')).name for p, _ in entry.occurrences):
            global_overrides.append((identifier, text))

    files = {}
    empty_manifests = set()
    for module in args.modules:
        directory = (args.output / f'CL{args.langshort}-Common/ModuleData/Languages' / args.langfolder_output / module
                     if run_type == 'module' else args.output / module / 'ModuleData/Languages' / args.langfolder_output)
        references = []
        for (owner, tag, attribute), entries in sorted(grouped.items()):
            if owner != module:
                continue
            name = f'{tag}.{attribute}-{args.subtitleext}.xml'
            files[directory / name] = xml_bytes(strings_xml(args.langid, sorted(entries), args.langalias))
            references.append('/'.join([args.langfolder_output] + ([module] if run_type == 'module' else []) + [name]))
        if module == 'Native':
            functions = args.mb2dir / 'Modules/Native/ModuleData/Languages' / args.langshort / args.functions
            if functions.is_file():
                files[directory / args.functions] = functions.read_bytes()
                references.append('/'.join([args.langfolder_output] + ([module] if run_type == 'module' else []) + [args.functions]))
        manifest = directory / 'language_data.xml'
        if references:
            files[manifest] = xml_bytes(
                language_data(args.langid, references, args.subtitleext, args.iso)
            )
        else:
            empty_manifests.add(manifest)
        if args.langalias and run_type == 'module':
            alias = args.output / f'CL{args.langshort}-Common/ModuleData/Languages' / (args.langfolder_output + '2') / module
            if references:
                files[alias / 'language_data.xml'] = xml_bytes(
                    language_data(
                        args.langalias, references, args.subtitleext, args.iso
                    )
                )
            else:
                empty_manifests.add(alias / 'language_data.xml')
    if run_type == 'module' and not args.no_english_overwriting:
        language_root = args.output / f'CL{args.langshort}-Common/ModuleData/Languages'
        references = []
        if global_overrides:
            relative = f'{args.langfolder_output}/Native/english-overrides-{args.subtitleext}.xml'
            files[language_root / relative] = xml_bytes(strings_xml('English', sorted(global_overrides)))
            references.append(relative)
        if references:
            files[language_root / 'language_data.xml'] = xml_bytes(
                language_data('English', references)
            )
        else:
            empty_manifests.add(language_root / 'language_data.xml')
    if run_type == 'module':
        common_root = args.output / f'CL{args.langshort}-Common/ModuleData/Languages'
        multiplayer_root = args.output / f'CL{args.langshort}-MP/ModuleData/Languages'

        def multiplayer_path(path):
            relative = path.relative_to(common_root)
            if relative == Path('language_data.xml') or (
                len(relative.parts) == 3
                and relative.parts[1] in ('Native', 'MultiPlayer')
            ):
                return multiplayer_root / relative
            return None

        # Keep Common intact and duplicate the selected modules, including
        # manifests, aliases, Native functions and English overrides.
        for path, data in list(files.items()):
            destination = multiplayer_path(path)
            if destination is not None:
                files[destination] = data
        for path in list(empty_manifests):
            destination = multiplayer_path(path)
            if destination is not None:
                empty_manifests.add(destination)

    # Build and validate everything before writing any output files.
    for path, data in files.items():
        ET.fromstring(data)
    # Remove obsolete manifests instead of keeping stale references or writing
    # empty language definitions. Do not remove translation files or folders.
    for path in empty_manifests:
        path.unlink(missing_ok=True)
    for path, data in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print(f'Wrote {len(files)} XML files ({sum(map(len, grouped.values()))} translations) to {args.output}')
    return files


def main(argv=None):
    config = defaults()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--langshort', default=config.get('langshort', 'JP'))
    parser.add_argument('--langid')
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output', type=Path, default=Path('Modules'))
    parser.add_argument('--mb2dir', type=Path, default=Path(config.get('mb2dir', GAME_DIR)))
    parser.add_argument('--modules', nargs='+', default=MODULES)
    parser.add_argument('--langfolder-output')
    parser.add_argument('--subtitleext', default='jp')
    parser.add_argument('--langsuffix', default='jpn', help='Accepted for compatibility; subtitleext controls new filenames')
    parser.add_argument('--functions')
    parser.add_argument('--iso', default=config.get('iso'))
    parser.add_argument('--langalias')
    parser.add_argument('--output-type', choices=['module', 'overwriter', 'both'], default='module')
    parser.add_argument('--with-id', action='store_true')
    parser.add_argument('--all-entries', action='store_true', default=config.get('all_entries', False))
    parser.add_argument('--skip-blank_vanilla', '--skip-blank-vanilla', action=argparse.BooleanOptionalAction,
                        default=config.get('skip_blank_vanilla', True))
    parser.add_argument('--no-english-overwriting', action='store_true', default=config.get('no_english_overwriting', False))
    args = parser.parse_args(argv)
    args.input = args.input or Path(f'text/MB2BL-{args.langshort}.po')
    args.langid = args.langid or (config.get('langid', '日本語') if args.langshort == config.get('langshort', 'JP') else args.langshort)
    args.langfolder_output = args.langfolder_output or args.langshort
    args.functions = args.functions or f'{args.langshort.lower()}_functions.xml'
    try:
        for name in [args.langshort, args.langfolder_output, args.subtitleext, args.functions] + args.modules:
            if not name or name in ('.', '..') or any(c in name for c in '/\\:'):
                raise ValueError(f'Expected a folder or filename component: {name!r}')
        catalog = polib.pofile(str(args.input), encoding='utf-8-sig')
        original, japanese = load_vanilla_translations(args)
        report_correction_rate(catalog, japanese)
        for run_type in (['module', 'overwriter'] if args.output_type == 'both' else [args.output_type]):
            export_catalog(args, run_type, catalog=catalog, original=original)
    except (OSError, ValueError, ET.XMLSyntaxError) as error:
        parser.exit(1, f'Error: {error}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
