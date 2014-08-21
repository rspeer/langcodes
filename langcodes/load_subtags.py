from langcodes.registry_parser import parse_registry
from langcodes.db import LanguageDB
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


def main(db_filename):
    # Create the database
    with LanguageDB(db_filename) as db:
        db.setup()
        load_registry(db, parse_registry(), 'en')


if __name__ == '__main__':
    db_filename = sys.argv[1]

    main(db_filename)
