import sqlite3
import json
from .util import data_filename


# Load some small amounts of data from .json that it's okay to reload on each
# import.
_LIKELY_SUBTAG_JSON = json.load(
    open(data_filename('cldr/supplemental/likelySubtags.json'))
)
LIKELY_SUBTAGS = _LIKELY_SUBTAG_JSON['supplemental']['likelySubtags']


def _make_language_match_data():
    match_json = json.load(
        open(data_filename('cldr/supplemental/languageMatching.json'))
    )
    matches = {}
    match_data = match_json['supplemental']['languageMatching']['written']
    for item in match_data:
        match = item['languageMatch']
        desired = match['_desired']
        supported = match['_supported']
        value = match['_percent']
        if (desired, supported) not in matches:
            matches[(desired, supported)] = int(value)
        if match.get('_oneway') != 'true':
            if (supported, desired) not in matches:
                matches[(supported, desired)] = int(value)
    return matches
LANGUAGE_MATCHING = _make_language_match_data()


_PARENT_LOCALE_JSON = json.load(
    open(data_filename('cldr/supplemental/parentLocales.json'), encoding='ascii')
)
PARENT_LOCALES = _PARENT_LOCALE_JSON['supplemental']['parentLocales']['parentLocale']


class LanguageDB:
    """
    The LanguageDB contains relational data about language subtags. It's
    originally read from a flatfile and .json files using load_subtags.py,
    and after that it's available in this SQLite database.
    """
    TABLES = [
        """CREATE TABLE IF NOT EXISTS language(
            subtag TEXT PRIMARY KEY COLLATE NOCASE,
            script TEXT NULL,
            is_macro INTEGER,
            is_collection INTEGER,
            preferred TEXT,
            macrolang TEXT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS extlang(
            subtag TEXT PRIMARY KEY COLLATE NOCASE,
            prefixes TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS language_name(
            subtag TEXT COLLATE NOCASE,
            language TEXT COLLATE NOCASE,
            name TEXT COLLATE NOCASE
        )""",
        """CREATE TABLE IF NOT EXISTS nonstandard(
            tag TEXT PRIMARY KEY COLLATE NOCASE,
            description TEXT,
            preferred TEXT NULL,
            is_macro INTEGER
        )""",
        """CREATE TABLE IF NOT EXISTS nonstandard_region(
            tag TEXT PRIMARY KEY COLLATE NOCASE,
            preferred TEXT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS region(
            subtag TEXT PRIMARY KEY COLLATE NOCASE,
            deprecated INTEGER,
            preferred TEXT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS region_name(
            subtag TEXT COLLATE NOCASE,
            language TEXT COLLATE NOCASE,
            name TEXT COLLATE NOCASE
        )""",
        # we have no useful information about scripts except their name
        """CREATE TABLE IF NOT EXISTS script_name(
            subtag TEXT COLLATE NOCASE,
            language TEXT COLLATE NOCASE,
            name TEXT COLLATE NOCASE
        )""",
        # was there a reason variants saved their comments?
        """CREATE TABLE IF NOT EXISTS variant(
            subtag TEXT PRIMARY KEY COLLATE NOCASE,
            prefixes TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS variant_name(
            subtag TEXT COLLATE NOCASE,
            language TEXT COLLATE NOCASE,
            name TEXT COLLATE NOCASE
        )""",
        """CREATE VIEW IF NOT EXISTS macrolanguages AS
            SELECT DISTINCT macrolang FROM language where macrolang is not NULL""",
    ]
    NAMES_TO_INDEX = ['language_name', 'region_name', 'script_name', 'variant_name']

    def __init__(self, db_filename):
        self.filename = db_filename

        # Because this is Python 3, we can set `check_same_thread=False` and
        # get a database that can be safely read in multiple threads. Hooray!
        self.conn = sqlite3.connect(db_filename, check_same_thread=False)

    def __str__(self):
        return "LanguageDB(%s)" % self.filename

    # Methods for initially creating the schema
    # =========================================

    def setup(self):
        for stmt in self.TABLES:
            self.conn.execute(stmt)
        self._make_indexes()

    def _make_indexes(self):
        for table_name in self.NAMES_TO_INDEX:
            self.conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS {0}_uniq ON {0}(subtag, language, name)".format(table_name)
            )
            self.conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS {0}_lookup ON {0}(subtag, language, name)".format(table_name)
            )

    # Methods for building the database
    # =================================

    def _add_row(self, table_name, values):
        tuple_template = ', '.join(['?'] * len(values))
        template = "INSERT OR IGNORE INTO %s VALUES (%s)" % (table_name, tuple_template)
        # I know, right? The sqlite3 driver doesn't let you parameterize the
        # table name. Good thing little Bobby Tables isn't giving us the names.
        self.conn.execute(template, values)

    def add_name(self, table, subtag, datalang, name):
        self._add_row('%s_name' % table, (subtag, datalang, name))

    def add_language(self, data, datalang):
        subtag = data['Subtag']
        script = data.get('Suppress-Script')
        is_macro = 'Macrolanguage' in data
        is_collection = (data.get('Scope') == 'collection')
        preferred = data.get('Preferred-Value')
        macrolang = data.get('Macrolanguage')

        self._add_row(
            'language',
            (subtag, script, is_macro, is_collection, preferred, macrolang)
        )
        for name in data['Description']:
            self.add_name('language', subtag, datalang, name)

    def add_extlang(self, data, _datalang):
        subtag = data['Subtag']
        prefixes = ';'.join(data.get('Prefix', '*'))
        self._add_row('extlang', (subtag, prefixes))

    def add_nonstandard(self, data, _datalang):
        tag = data['Tag']
        desc = ';'.join(data.get('Description'))
        preferred = data.get('Preferred-Value')
        self.add_language_mapping(tag, desc, preferred, False)

    def add_language_mapping(self, tag, desc, preferred, is_macro):
        self._add_row('nonstandard', (tag, desc, preferred, is_macro))

    def add_region(self, data, datalang):
        subtag = data['Subtag']
        deprecated = 'Deprecated' in data
        preferred = data.get('Preferred-Value')

        self._add_row('region', (subtag, deprecated, preferred))
        for name in data['Description']:
            self.add_name('region', subtag, datalang, name)

    def add_region_mapping(self, tag, preferred):
        self._add_row('nonstandard_region', (tag, preferred))

    def add_script(self, data, datalang):
        subtag = data['Subtag']
        for name in data['Description']:
            self.add_name('script', subtag, datalang, name)

    def add_variant(self, data, datalang):
        subtag = data['Subtag']
        prefixes = ';'.join(data.get('Prefix', '*'))
        self._add_row('variant', (subtag, prefixes))

        for name in data['Description']:
            self.add_name('variant', subtag, datalang, name)

    # Iterating over things in the database
    # =====================================

    def query(self, query, *args):
        c = self.conn.cursor()
        c.execute(query, args)
        return c.fetchall()

    def macrolanguages(self):
        return self.query(
            "select subtag, macrolang from language "
            "where macrolang is not null"
        )

    def language_replacements(self, macro=False):
        return self.query(
            "select tag, preferred from nonstandard where is_macro=? "
            "and preferred is not null", macro
        )
        return c.fetchall()

    def region_replacements(self):
        return self.query(
            "select tag, preferred from nonstandard_region "
            "where preferred is not null"
        )

    def suppressed_scripts(self):
        return self.query(
            "select subtag, script from language "
            "where script is not null"
        )

    # Looking up names of things
    # ==========================

    def names_for(self, table_name, subtag):
        results = {}
        items = self.query(
            ("select language, name from {}_name "
             "where subtag == ?".format(table_name)), subtag
        )
        for language, name in items:
            if language not in results:
                results[language] = name
        return results

    def lookup_name(self, table_name, name, language):
        return [row[0] for row in self.query(
            "select subtag from {}_name where language == ? and "
            "name == ?".format(table_name),
            language, name
        )]

    def lookup_name_prefix(self, table_name, name, language):
        return self.query(
            "select subtag, name from {}_name where language == ? and "
            "(name == ? or name like ?)".format(table_name),
            language, name, name + '%'
        )

    # Using the database as a context manager
    # =======================================

    def close(self):
        self.conn.commit()
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()
