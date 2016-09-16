from langcodes.registry_parser import parse_registry
from langcodes.db import LanguageDB
from langcodes.util import data_filename
from pathlib import Path
import json


def load_registry(db, registry_data, datalang='en'):
    for item in registry_data:
        typ = item['Type']
        if typ == 'language':
            db.add_language(item, datalang, name_order=10)
        elif typ == 'extlang':
            db.add_extlang(item, datalang)
        elif typ in {'grandfathered', 'redundant'}:
            db.add_nonstandard(item, datalang)
        elif typ == 'region':
            db.add_region(item, datalang, name_order=10)
        elif typ == 'script':
            db.add_script(item, datalang, name_order=10)
        elif typ == 'variant':
            db.add_variant(item, datalang, name_order=10)
        else:
            print("Ignoring type: %s" % typ)


# Usually we can just rely on CLDR's names for languages. In some cases, we
# need to avoid learning certain names from most sources, to prevent ambiguity
# across different sources. Names in this set will only be learned from the
# IANA registry.
#
# The two ambiguous cases are:
#
# - 'Ladin' is the English name for Ladin (lld), a language of northern Italy;
#   it is also the Azerbaijani name for Ladino (lad), a dialect of Old Spanish.
#
# - 'Fala' is the English name for Fala (fax) and the Kwasio name for French
#   (fr).
#
# CLDR avoids ambiguity like this within its own data, but here the problem is
# that Wiktionary knows about Ladin and CLDR only knows about Ladino, so we
# need to manually block the name.
#
# Also, we don't want to accidentally name a language with the null string.

BLOCKED_NAMES = {
    'ladin', 'fala', '',
}


def load_cldr_file(db, typ, langcode, path):
    data = json.load(path.open(encoding='utf-8'))
    closer = data['main'][langcode]['localeDisplayNames']
    for actual_data in closer.values():
        for subtag, name in actual_data.items():
            if subtag == name:
                # Default entries that map a language code to itself, which
                # a lazy annotator just left there
                continue
            order = 0
            # CLDR assigns multiple names to one code by adding -alt-* to
            # the end of the code. For example, the English name of 'az' is
            # Azerbaijani, but the English name of 'az-alt-short' is Azeri.
            if '-alt-' in subtag:
                subtag, _ = subtag.split('-alt-', 1)
                order = 1
            if typ == 'variant':
                subtag = subtag.lower()

            if name.lower() not in BLOCKED_NAMES:
                db.add_name(typ, subtag, langcode, name, order)


def load_cldr_aliases(db, path):
    data = json.load(path.open(encoding='utf-8'))
    lang_aliases = data['supplemental']['metadata']['alias']['languageAlias']
    for subtag, value in lang_aliases.items():
        if '_replacement' in value:
            preferred = value['_replacement']
            is_macro = value['_reason'] == 'macrolanguage'
            db.add_language_mapping(subtag, None, preferred, is_macro)
    region_aliases = data['supplemental']['metadata']['alias']['territoryAlias']
    for subtag, value in region_aliases.items():
        if '_replacement' in value:
            preferred = value['_replacement']
            if ' ' in preferred:
                # handling regions that have split up is a difficult detail that
                # we don't care to implement yet
                preferred = None
            db.add_region_mapping(subtag, preferred)


def load_custom_aliases(db, path):
    """
    Load custom language aliases that are given in a CSV file.
    """
    data = path.open(encoding='utf-8')
    for line in data:
        typ, datalang, subtag, name = line.rstrip().split(',', 3)
        if name.lower() not in BLOCKED_NAMES:
            db.add_name(
                table=typ,
                subtag=subtag,
                datalang=datalang,
                name=name,
                order=1000
            )


def load_cldr(db, cldr_path):
    main_path = cldr_path / 'main'
    for subpath in main_path.iterdir():
        if subpath.is_dir() and (subpath / 'languages.json').exists():
            langcode = subpath.name
            load_cldr_file(db, 'language', langcode, subpath / 'languages.json')
            load_cldr_file(db, 'region', langcode, subpath / 'territories.json')
            load_cldr_file(db, 'script', langcode, subpath / 'scripts.json')
            load_cldr_file(db, 'variant', langcode, subpath / 'variants.json')
    load_cldr_aliases(db, cldr_path / 'supplemental' / 'aliases.json')


def load_wiktionary_codes(db, datalang, path):
    for line in path.open(encoding='utf-8'):
        code, canonical, family, script, othernames = line.rstrip('\n').split('\t')[:5]
        names = [canonical] + [name.strip() for name in othernames.split(',')]
        for i, name in enumerate(names):
            if name.lower() not in BLOCKED_NAMES:
                db.add_name(
                    table='language',
                    subtag=code,
                    datalang=datalang,
                    name=name,
                    order=2000 + i
                )


def main():
    # Create the database
    with LanguageDB(data_filename('subtags.db')) as db:
        db.setup()
        load_cldr(db, Path(data_filename('cldr')))
        load_registry(db, parse_registry(), 'en')
        load_custom_aliases(db, Path(data_filename('aliases.csv')))
        load_wiktionary_codes(db, 'en', Path(data_filename('wiktionary/codes-en.csv')))


if __name__ == '__main__':
    main()
