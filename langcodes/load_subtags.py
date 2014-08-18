'''
Parser the language-subtag-registry file and creates a SQLite database from it
with six tables.

Run the script with two arguments, in this order: input file, database file.

The input file is available here:
http://www.iana.org/assignments/language-subtag-registry/language-subtag-registry
'''
import codecs
import contextlib
import sqlite3
import sys


TABLES = [
    """CREATE TABLE IF NOT EXISTS language(
        tag TEXT,
        desc TEXT,
        script TEXT,
        is_macro INTEGER,
        is_collection INTEGER,
        preferred TEXT,
        macrolang TEXT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS nonstandard(
        tag TEXT,
        desc TEXT,
        preferred TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS extlang(
        tag TEXT,
        desc TEXT,
        prefix TEXT,
        macrolang TEXT,
        preferred TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS region(
        tag TEXT,
        desc TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS script(
        tag TEXT,
        desc TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS variant(
        tag TEXT,
        prefix TEXT,
        desc TEXT,
        comment TEXT
    )""",
    """CREATE VIEW IF NOT EXISTS macrolanguages AS
        SELECT DISTINCT macrolang FROM language where macrolang is not NULL""",
]
INDEXES = [
    "CREATE UNIQUE INDEX IF NOT EXISTS langs_uniq ON language(tag)",
    "CREATE UNIQUE INDEX IF NOT EXISTS nonstandard_uniq ON nonstandard(tag)",
    "CREATE UNIQUE INDEX IF NOT EXISTS extlang_uniq ON extlang(tag)",
    "CREATE UNIQUE INDEX IF NOT EXISTS region_uniq ON region(tag)",
    "CREATE UNIQUE INDEX IF NOT EXISTS script_uniq ON script(tag)",
    "CREATE UNIQUE INDEX IF NOT EXISTS variant_uniq ON variant(tag)",
]


class Language(dict):
    def __init__(self, code):
        self['code'] = code
        self['script'] = None
        self['desc'] = []
        self['macrolang'] = None
        self['preferred'] = code
        self.is_macrolang = 0
        self.is_collection = 0

    def to_row(self):
        return (self['code'], ';'.join(self['desc']), self['script'],
                self.is_macrolang, self.is_collection, self['macrolang'],
                self['preferred'])


class Variant(dict):
    def __init__(self, tag):
        self['tag'] = tag
        self['prefix'] = []
        self['desc'] = []
        self['comment'] = None

    def to_row(self):
        return (self['tag'], ';'.join(self['prefix']), ';'.join(self['desc']),
                self['comment'])


class Extlang(dict):
    def __init__(self, tag):
        self['tag'] = tag
        self['desc'] = []
        self['prefix'] = []
        self['preferred'] = self['tag']
        self['macrolang'] = None

    def to_row(self):
        return (self['tag'], ';'.join(self['desc']), ';'.join(self['prefix']),
                self['macrolang'], self['preferred'])


def load_file(filename, conn):
    '''
    Reads the content of the subtags file and populates various tables with its
    values.
    '''
    variants = []
    languages = []
    extlangs = []

    lang = None
    extlang = None
    variant = None
    _type = None
    tag = None
    key = None
    desc = []
    comment = []
    nonstandard = False
    with codecs.open(filename, 'r', encoding='utf-8') as ifp:
        prevline = ''
        for line in ifp:
            if line.startswith('  '):
                prevline += ' ' + line.strip()

            prevline = line
            if prevline.startswith('%%'):
                if not nonstandard:
                    if lang:
                        languages.append(lang)
                    elif extlang:
                        extlangs.append(extlang)
                    elif variant:
                        if comment:
                            variant['comment'] = ' '.join(comment)
                        variants.append(variant)
                    elif _type == 'script':
                        conn.execute('insert into script values (?, ?)',
                                     (tag, ';'.join(desc)))
                    elif _type == 'region':
                            conn.execute('insert into region values (?, ?)',
                                         (tag, ';'.join(desc)))
                else:
                    if lang['preferred'] != lang['code']:
                        lang['desc'] = ';'.join(desc)
                        conn.execute('insert into nonstandard values(?, ?, ?)',
                                     (lang['code'], lang['desc'],
                                      lang['preferred']))
                nonstandard = False
                _type = None
                tag = None
                lang = None
                extlang = None
                variant = None
                desc = []
                comment = []
            else:
                try:
                    (key, value) = prevline.strip().split(': ')
                    if value in ['grandfathered', 'redundant']:
                        nonstandard = True
                    if key == 'Type':
                        _type = value
                    elif key in 'Subtag':
                        if _type == 'language':
                            lang = Language(value)
                        elif _type == 'extlang':
                            extlang = Extlang(value)
                        elif _type == 'variant':
                            variant = Variant(value)
                        tag = value
                    elif key == 'Tag':
                        lang = Language(value)
                    elif key == 'Description':
                        if _type == 'language':
                            lang['desc'].append(value)
                            tag = lang['desc'][-1]
                        elif _type == 'variant':
                            variant['desc'].append(value)
                        elif _type == 'extlang':
                            extlang['desc'].append(value)
                        else:
                            desc.append(value)
                    elif key == 'Scope':
                        if value == 'macrolanguage' and lang:
                            lang.is_macrolang = 1
                        elif value == 'collection' and lang:
                            lang.is_collection = 1
                    elif key == 'Macrolanguage':
                        if lang:
                            lang['macrolang'] = value
                        elif extlang:
                            extlang['macrolang'] = value
                    elif key == 'Comments':
                        comment.append(value)
                    elif key == 'Prefix':
                        if variant:
                            variant['prefix'].append(value)
                        elif extlang:
                            extlang['prefix'].append(value)
                    elif key == 'Suppress-Script' and lang:
                        lang['script'] = value
                    elif key == 'Preferred-Value':
                        if lang:
                            lang['preferred'] = value
                        elif extlang:
                            extlang['preferred'] = value
                except ValueError:
                    # No colon in the text: may be the continuation of a
                    # comment from the previous line
                    if line.startswith('  '):
                        comment.append(line.strip())

    for lang in languages:
        conn.execute('insert into language values (?, ?, ?, ?, ?, ?, ?)',
                     lang.to_row())
    for variant in variants:
        conn.execute('insert into variant values (?, ?, ?, ?)',
                     variant.to_row())
    for extlang in extlangs:
        conn.execute('insert into extlang values (?, ?, ?, ?, ?)',
                     extlang.to_row())


def main(iana_file, db_file):
    # Create the database
    with contextlib.closing(sqlite3.connect(db_file)) as conn:
        # Create tables
        for stmt in TABLES + INDEXES:
            conn.execute(stmt)
        # Populate the tables from the subtag file
        load_file(iana_file, conn)
        conn.commit()
    return 0

if __name__ == '__main__':
    iana_file = sys.argv[1]
    db_file = sys.argv[2]

    sys.exit(main(iana_file, db_file))
