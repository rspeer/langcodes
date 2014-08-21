import sqlite3

class LanguageDB:
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
        self.conn = sqlite3.connect(db_filename)

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

    def _add_row(self, table_name, values):
        tuple_template = ', '.join(['?'] * len(values))
        template = "INSERT OR IGNORE INTO %s VALUES (%s)" % (table_name, tuple_template)
        # I know, right? The sqlite3 driver doesn't let you parameterize the
        # table name. Good thing Bobby Tables isn't giving us the names.
        self.conn.execute(template, values)

    def add_name(self, table, subtag, datalang, name):
        self._add_row('%s_name' % table, (subtag, datalang, name))
    
    def add_language(self, data, datalang):
        subtag = data['Subtag']
        script = data.get('Script')
        is_macro = 'Macrolanguage' in data
        is_collection = (data.get('Scope') == 'Collection')
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
        self._add_row('nonstandard', (tag, desc, preferred))

    def add_region(self, data, datalang):
        subtag = data['Subtag']
        deprecated = 'Deprecated' in data
        preferred = data.get('Preferred-Value')
        
        self._add_row('region', (subtag, deprecated, preferred))
        for name in data['Description']:
            self.add_name('region', subtag, datalang, name)

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
    
    def close(self):
        self.conn.commit()
        self.conn.close()
    
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def __str__(self):
        return "LanguageDB(%s)" % self.filename
