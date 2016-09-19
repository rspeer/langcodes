import sqlite3
import json
from .util import data_filename


# Load some small amounts of data from .json that it's okay to reload on each
# import.
class lazy_property(object):
    '''
    A lazy_property decorator from StackOverflow:
    http://stackoverflow.com/a/6849299/773754
    '''

    def __init__(self, fget):
        self.fget = fget
        self.func_name = fget.__name__

    def __get__(self, obj, cls):
        if obj is None:
            return None
        value = self.fget(obj)
        setattr(obj, self.func_name, value)
        return value


class LanguageDB:
    """
    The LanguageDB contains relational data about language subtags. It's
    originally read from a flatfile and .json files using load_subtags.py.
    After that it's available primarily through a SQLite database.

    Some information that doesn't fit into the SQL schema is loaded lazily from
    .json files.
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
            name TEXT COLLATE NOCASE,
            entry_order INTEGER
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
            name TEXT COLLATE NOCASE,
            entry_order INTEGER
        )""",
        # we have no useful information about scripts except their name
        """CREATE TABLE IF NOT EXISTS script_name(
            subtag TEXT COLLATE NOCASE,
            language TEXT COLLATE NOCASE,
            name TEXT COLLATE NOCASE,
            entry_order INTEGER
        )""",
        # was there a reason variants saved their comments?
        """CREATE TABLE IF NOT EXISTS variant(
            subtag TEXT PRIMARY KEY COLLATE NOCASE,
            prefixes TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS variant_name(
            subtag TEXT COLLATE NOCASE,
            language TEXT COLLATE NOCASE,
            name TEXT COLLATE NOCASE,
            entry_order INTEGER
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
                "CREATE INDEX IF NOT EXISTS {0}_lookup ON {0}(subtag, language)".format(table_name)
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS {0}_lookup_name ON {0}(name)".format(table_name)
            )

    # Methods for building the database
    # =================================

    def _add_row(self, table_name, values):
        tuple_template = ', '.join(['?'] * len(values))
        template = "INSERT OR IGNORE INTO %s VALUES (%s)" % (table_name, tuple_template)
        # I know, right? The sqlite3 driver doesn't let you parameterize the
        # table name. Good thing little Bobby Tables isn't giving us the names.
        self.conn.execute(template, values)

    def add_name(self, table, subtag, datalang, name, order):
        if name == subtag:
            return
        self._add_row('%s_name' % table, (subtag, datalang, name, order))

        # Handle multiple forms of language names in Chinese
        if '文' in name:
            self._add_row('%s_name' % table, (subtag, datalang, name.replace('文', '语'), order + 100))
            self._add_row('%s_name' % table, (subtag, datalang, name.replace('文', '語'), order + 100))

    def add_language(self, data, datalang, name_order=0):
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

        # If this is a deprecated tag that points to another language
        # (using a Preferred-Value field), then make sure to add it using
        # `add_language_mapping`, the same way we would for a 'grandfathered'
        # or 'redundant' entry.
        #
        # For other kinds of subtags, we'll find the mappings we need later in
        # the CLDR data, but we take language mappings from the IANA data
        # when we find them because there are more languages in IANA than CLDR.
        if preferred:
            desc = ';'.join(data.get('Description', []))
            self.add_language_mapping(
                subtag, desc, preferred, False
            )

            # Make sure the names for unnormalized codes rank below all other
            # ones.
            name_order += 10000

        # Even if there's a mapping to another language code, we should still
        # add its description; it might be the only way we know that name,
        # such as 'Moldavian'.
        for i, name in enumerate(data['Description']):
            self.add_name('language', subtag, datalang, name, i + name_order)

            # Allow, for example, "Hakka" to match "Hakka Chinese"
            if name.endswith(' Chinese'):
                self.add_name('language', subtag, datalang, name[:-8], i + name_order + 100)

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

    def add_region(self, data, datalang, name_order=0):
        subtag = data['Subtag']
        deprecated = 'Deprecated' in data
        preferred = data.get('Preferred-Value')

        self._add_row('region', (subtag, deprecated, preferred))
        for i, name in enumerate(data['Description']):
            self.add_name('region', subtag, datalang, name, i + name_order)

    def add_region_mapping(self, tag, preferred):
        self._add_row('nonstandard_region', (tag, preferred))

    def add_script(self, data, datalang, name_order=0):
        subtag = data['Subtag']
        for i, name in enumerate(data['Description']):
            self.add_name('script', subtag, datalang, name, i + name_order)

    def add_variant(self, data, datalang, name_order=0):
        subtag = data['Subtag']
        prefixes = ';'.join(data.get('Prefix', '*'))
        self._add_row('variant', (subtag, prefixes))

        for i, name in enumerate(data['Description']):
            self.add_name('variant', subtag, datalang, name, i + name_order)

    # Iterating over things in the database
    # =====================================

    def query(self, query, *args):
        c = self.conn.cursor()
        c.execute(query, args)
        return c.fetchall()

    def list_macrolanguages(self):
        return self.query(
            "select subtag, macrolang from language "
            "where macrolang is not null"
        )

    def language_replacements(self, macro=False):
        return self.query(
            "select tag, preferred from nonstandard where is_macro=? "
            "and preferred is not null", macro
        )

    def region_replacements(self):
        return self.query(
            "select tag, preferred from nonstandard_region "
            "where preferred is not null"
        )

    def list_suppressed_scripts(self):
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
             "where subtag == ? order by subtag, language, entry_order"
             .format(table_name)), subtag
        )
        for language, name in items:
            if language not in results:
                results[language] = name
        return results

    def lookup_name(self, table_name, name):
        """
        Formerly `lookup_name_in_any_language`. Given a natural-language name,
        find the code that it refers to. `table_name` can be 'language',
        'script', or 'region'.

        We no longer care about the language we're supposed to find the
        language name in, because there are no longer ambiguities that
        depend on the language. "French" only ever refers to one language,
        as does "francés" or "français".
        """
        rows = [row for row in self.query(
            "select subtag from {}_name where name == ? order by entry_order, language limit 1"
            .format(table_name),
            name
        )]
        if not rows:
            raise LookupError("Can't find any %s named %r" % (table_name, name))
        else:
            return rows[0][0]

    def lookup_name_multiple(self, table_name, name):
        """
        Return all of the best-matching rows in a table of names.  Used for
        testing that name lookups are never ambiguous.
        """
        rows = [row for row in self.query(
            "select subtag, language, entry_order from {}_name where name == ? order by entry_order"
            .format(table_name),
            name
        )]
        if not rows:
            return []
        else:
            best_rank = min([row[2] for row in rows])
            return [row for row in rows if row[2] == best_rank]

    # Cached dictionaries of information
    # ==================================

    @lazy_property
    def normalized_languages(self):
        """
        Non-standard codes that should be unconditionally replaced.
        """
        results = {orig.lower(): new.lower()
                   for (orig, new) in self.language_replacements()}

        # one more to handle the 'root' locale
        results['root'] = 'und'
        return results

    @lazy_property
    def normalized_macrolanguages(self):
        """
        Codes that the Unicode Consortium would rather replace with macrolanguages.
        """
        return {
            orig.lower(): new
            for (orig, new) in self.language_replacements(macro=True)
        }

    @lazy_property
    def macrolanguages(self):
        """
        Mappings for all languages that have macrolanguages.
        """
        return {lang: macro for (lang, macro) in self.list_macrolanguages()}

    @lazy_property
    def normalized_regions(self):
        """
        Regions that have been renamed, merged, or re-coded. (This package doesn't
        handle the ones that have been split, like Yugoslavia.)
        """
        return {
            orig.upper(): new.upper()
            for (orig, new) in self.region_replacements()
        }

    @lazy_property
    def default_scripts(self):
        """
        Most languages imply a particular script that they should be written in.
        This data is used by the `assume_script` and `simplify_script` methods.
        """
        return {
            lang: script
            for (lang, script) in self.list_suppressed_scripts()
        }

    @lazy_property
    def parent_locales(self):
        """
        CLDR's list of which locales are "parents" of other locales.
        """
        pl_json = json.load(
            open(data_filename('cldr/supplemental/parentLocales.json'), encoding='ascii')
        )
        return pl_json['supplemental']['parentLocales']['parentLocale']

    @lazy_property
    def likely_subtags(self):
        """
        Information on which subtag values are most likely given other subtags.
        """
        ls_json = json.load(
            open(data_filename('cldr/supplemental/likelySubtags.json'))
        )
        return ls_json['supplemental']['likelySubtags']

    # Using the database as a context manager
    # =======================================

    def close(self):
        self.conn.commit()
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()


# Load the SQLite database that contains the data we need about languages.
DB = LanguageDB(data_filename('subtags.db'))
