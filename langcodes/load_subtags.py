from langcodes.registry_parser import parse_registry
from langcodes.db import LanguageDB
from langcodes.util import data_filename
from pathlib import Path
import json
import sys


def load_registry(db, registry_data, datalang='en'):
    for item in registry_data:
        typ = item['Type']
        if typ == 'language':
            db.add_language(item, datalang)
        elif typ == 'extlang':
            db.add_extlang(item, datalang)
        elif typ in {'grandfathered', 'redundant'}:
            db.add_nonstandard(item, datalang)
        elif typ == 'region':
            db.add_region(item, datalang)
        elif typ == 'script':
            db.add_script(item, datalang)
        elif typ == 'variant':
            db.add_variant(item, datalang)
        else:
            print("Ignoring type: %s" % typ)


def load_cldr_file(db, typ, langcode, path):
    data = json.load(path.open(encoding='utf-8'))
    closer = data['main'][langcode]['localeDisplayNames']
    for actual_data in closer.values():
        for subtag, name in actual_data.items():
            if '-alt-' in subtag:
                subtag, _ = subtag.split('-alt-', 1)
            if typ == 'variant':
                subtag = subtag.lower()
            db.add_name(typ, subtag, langcode, name)


def load_language_aliases(db, path):
    data = json.load(path.open(encoding='utf-8'))
    lang_aliases = data['supplemental']['metadata']['alias']['languageAlias']
    for subtag, value in lang_aliases.items():
        if '_replacement' in value:
            preferred = value['_replacement']
            is_macro = value['_reason'] == 'macrolanguage'
            db.add_nonstandard_mapping(subtag, None, preferred, is_macro)


def load_bibliographic_aliases(db, path):
    for line in path.open(encoding='utf-8'):
        biblio, preferred, name = line.rstrip().split(',', 2)
        desc = '%s (bibliographic code)' % name
        db.add_nonstandard_mapping(biblio, desc, preferred, False)


def load_cldr(db, cldr_path):
    main_path = cldr_path / 'main'
    for subpath in main_path.iterdir():
        if subpath.is_dir() and (subpath / 'languages.json').exists():
            langcode = subpath.name
            load_cldr_file(db, 'language', langcode, subpath / 'languages.json')
            load_cldr_file(db, 'region', langcode, subpath / 'territories.json')
            load_cldr_file(db, 'script', langcode, subpath / 'scripts.json')
            load_cldr_file(db, 'variant', langcode, subpath / 'variants.json')
    load_language_aliases(db, cldr_path / 'supplemental' / 'metadata.json')


def main(db_filename):
    # Create the database
    with LanguageDB(db_filename) as db:
        db.setup()
        load_registry(db, parse_registry(), 'en')
        load_cldr(db, Path(data_filename('cldr')))
        load_bibliographic_aliases(db, Path(data_filename('bibliographic_codes.csv')))


if __name__ == '__main__':
    db_filename = sys.argv[1]

    main(db_filename)
