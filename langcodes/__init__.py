# coding: utf-8
from __future__ import print_function, division, unicode_literals
from .tag_parser import parse
from .db import LanguageDB, LIKELY_SUBTAGS, LANGUAGE_MATCHING, PARENT_LOCALES
from .util import data_filename

DB = LanguageDB(data_filename('subtags.db'))

# When we're getting natural language information *about* languages, what
# language should it be in by default?
DEFAULT_LANGUAGE = 'en-US'

# Non-standard codes that should be unconditionally replaced.
NORMALIZED_LANGUAGES = {orig.lower(): new.lower()
                        for (orig, new) in DB.language_replacements()}

# Codes that the Unicode Consortium would rather replace with macrolanguages.
NORMALIZED_MACROLANGUAGES = {
    orig.lower(): new
    for (orig, new) in DB.language_replacements(macro=True)
}

# Mappings for all languages that have macrolanguages.
MACROLANGUAGES = {lang: macro for (lang, macro) in DB.macrolanguages()}


# Regions that have been renamed, merged, or re-coded. (This package doesn't
# handle the ones that have been split, like Yugoslavia.)
NORMALIZED_REGIONS = {
    orig.upper(): new.upper()
    for (orig, new) in DB.region_replacements()
}

DEFAULT_SCRIPTS = {
    lang: script
    for (lang, script) in DB.suppressed_scripts()
}


class LanguageData:
    ATTRIBUTES = ['language', 'macrolanguage', 'extlangs', 'script', 'region',
                  'variants', 'extensions', 'private']

    BROADER_KEYSETS = [
        {'language', 'script', 'region'},
        {'language', 'script'},
        {'language', 'region'},
        {'language'},
        {'macrolanguage', 'script', 'region'},
        {'macrolanguage', 'script'},
        {'macrolanguage', 'region'},
        {'macrolanguage'},
        {'script', 'region'},
        {'script'},
        {'region'},
        {}
    ]

    MATCHABLE_KEYSETS = [
        {'language', 'script', 'region'},
        {'language', 'script'},
        {'language'},
    ]

    def __init__(self, language=None, macrolanguage=None, extlangs=None,
                 script=None, region=None, variants=None, extensions=None,
                 private=None):
        self.language = language or macrolanguage
        self.macrolanguage = macrolanguage or language
        self.extlangs = extlangs
        self.script = script
        self.region = region
        self.variants = variants
        self.extensions = extensions
        self.private = private

    def __repr__(self):
        items = []
        for attr in self.ATTRIBUTES:
            if getattr(self, attr):
                if not (attr == 'macrolanguage'
                        and self.macrolanguage == self.language):
                    items.append('{0}={1!r}'.format(attr, getattr(self, attr)))
        return "LanguageData({})".format(', '.join(items))

    def __str__(self):
        return self.to_tag()

    def __getitem__(self, key):
        if key in self.ATTRIBUTES:
            return getattr(self, key)
        else:
            raise KeyError(key)

    def __contains__(self, key):
        return key in self.ATTRIBUTES and getattr(self, key)

    def __eq__(self, other):
        if not isinstance(other, LanguageData):
            return False
        return self.to_dict() == other.to_dict()

    def to_dict(self):
        """
        Get a dictionary of the attributes of this LanguageData object, which
        can be useful for constructing a similar object.
        """
        result = {}
        for key in self.ATTRIBUTES:
            value = getattr(self, key)
            if value:
                result[key] = value
        return result

    def update(self, other):
        """
        Update this LanguageData with the fields of another LanguageData.
        """
        return LanguageData(
            language=other.language or self.language,
            macrolanguage=other.macrolanguage or self.macrolanguage,
            extlangs=other.extlangs or self.extlangs,
            script=other.script or self.script,
            region=other.region or self.region,
            variants=other.variants or self.variants,
            extensions=other.extensions or self.extensions,
            private=other.private or self.private
        )

    def update_dict(self, newdata):
        """
        Update the attributes of this LanguageData from a dictionary.
        """
        return LanguageData(
            language=newdata.get('language', self.language),
            macrolanguage=newdata.get('macrolanguage', self.macrolanguage),
            extlangs=newdata.get('extlangs', self.extlangs),
            script=newdata.get('script', self.script),
            region=newdata.get('region', self.region),
            variants=newdata.get('variants', self.variants),
            extensions=newdata.get('extensions', self.extensions),
            private=newdata.get('private', self.private)
        )

    @staticmethod
    def parse(tag, normalize=True):
        """
        Create a LanguageData object from a language tag string.

        If normalize=True, non-standard or overlong tags will be replaced as
        they're interpreted. This is recommended.

        >>> LanguageData.parse('en-US')
        LanguageData(language='en', region='US')

        >>> LanguageData.parse('sh-QU')        # transform deprecated tags
        LanguageData(language='sr', macrolanguage='sh', script='Latn', region='EU')

        >>> LanguageData.parse('sgn-US')
        LanguageData(language='ase')

        >>> LanguageData.parse('sgn-US', normalize=False)
        LanguageData(language='sgn', region='US')

        >>> LanguageData.parse('zh-cmn-Hant')  # promote extlangs to languages
        LanguageData(language='cmn', macrolanguage='zh', script='Hant')

        >>> LanguageData.parse('zh-cmn-Hant', normalize=False)
        LanguageData(language='zh', extlangs=['cmn'], script='Hant')

        >>> LanguageData.parse('und')
        LanguageData()
        """
        data = {}
        # if the complete tag appears as something to normalize, do the
        # normalization right away. Smash case when checking, because the
        # case normalization that comes from parse() hasn't been applied yet.
        if normalize and tag.lower() in NORMALIZED_LANGUAGES:
            tag = NORMALIZED_LANGUAGES[tag.lower()]

        components = parse(tag)

        for typ, value in components:
            if typ == 'extlang' and normalize and data['language']:
                # smash extlangs when possible
                minitag = '%s-%s' % (data['language'], value)
                if minitag in NORMALIZED_LANGUAGES:
                    norm = NORMALIZED_LANGUAGES[minitag]
                    data.update(
                        LanguageData.parse(norm, normalize).to_dict()
                    )
                else:
                    data.setdefault(typ + 's', []).append(value)
            elif typ in {'extlang', 'variant', 'extension'}:
                data.setdefault(typ + 's', []).append(value)
            elif typ == 'language':
                if value == 'und':
                    pass
                elif normalize and value in NORMALIZED_LANGUAGES:
                    replacement = NORMALIZED_LANGUAGES[value]
                    # parse the replacement if necessary -- this helps with
                    # Serbian and Moldovan
                    data.update(
                        LanguageData.parse(replacement, normalize).to_dict()
                    )
                else:
                    data[typ] = value
                    if value in MACROLANGUAGES:
                        data['macrolanguage'] = MACROLANGUAGES[value]
            elif typ == 'region':
                if normalize and value in NORMALIZED_REGIONS:
                    data[typ] = NORMALIZED_REGIONS[value]
                else:
                    data[typ] = value
            else:
                data[typ] = value

        return LanguageData(**data)

    def to_tag(self):
        """
        Convert a LanguageData back to a standard language tag, as a string.
        This is also the str() representation of a LanguageData object.

        >>> LanguageData(language='en', region='GB').to_tag()
        u'en-GB'

        >>> LanguageData(language='yue', macrolanguage='zh', script='Hant',
        ...              region='HK').to_tag()
        u'yue-Hant-HK'

        >>> str(LanguageData(script='Arab'))
        'und-Arab'

        >>> str(LanguageData(region='IN'))
        'und-IN'
        """
        subtags = ['und']
        if self.language:
            subtags[0] = self.language
        elif self.macrolanguage:
            subtags[0] = self.macrolanguage
        if self.extlangs:
            for extlang in sorted(self.extlangs):
                subtags.append(extlang)
        if self.script:
            subtags.append(self.script)
        if self.region:
            subtags.append(self.region)
        if self.variants:
            for variant in sorted(self.variants):
                subtags.append(variant)
        if self.extensions:
            for ext in self.extensions:
                subtags.append(ext)
        if self.private:
            subtags.append(self.private)
        return '-'.join(subtags)

    def simplify_script(self):
        """
        Remove the script from some parsed language data, if the script is
        redundant with the language.

        >>> LanguageData(language='en', script='Latn').simplify_script()
        LanguageData(language='en')

        >>> LanguageData(language='yi', script='Latn').simplify_script()
        LanguageData(language='yi', script='Latn')

        >>> LanguageData(language='yi', script='Hebr').simplify_script()
        LanguageData(language='yi')
        """
        if self.language and self.script:
            if DEFAULT_SCRIPTS.get(self.language) == self.script:
                return self.update_dict({'script': None})

        return self

    def assume_script(self):
        """
        Fill in the script if it's missing, and if it can be assumed from the
        language subtag. This is the opposite of `simplify_script`.

        >>> LanguageData(language='en').assume_script()
        LanguageData(language='en', script='Latn')

        >>> LanguageData(language='yi').assume_script()
        LanguageData(language='yi', script='Hebr')

        >>> LanguageData(language='yi', script='Latn').assume_script()
        LanguageData(language='yi', script='Latn')

        This fills in nothing when the script cannot be assumed -- such as when
        the language has multiple scripts, or it has no standard orthography:

        >>> LanguageData(language='sr').assume_script()
        LanguageData(language='sr')

        >>> LanguageData(language='eee').assume_script()
        LanguageData(language='eee')

        It also dosn't fill anything in when the language is unspecified.

        >>> LanguageData(region='US').assume_script()
        LanguageData(region='US')
        """
        if self.language and not self.script:
            try:
                return self.update_dict({'script': DEFAULT_SCRIPTS[self.language]})
            except KeyError:
                return self
        else:
            return self

    def prefer_macrolanguage(self):
        """
        BCP 47 doesn't specify what to do with macrolanguages and the languages
        they contain. The Unicode CLDR, on the other hand, says that when a
        macrolanguage has a dominant standardized language, the macrolanguage
        code should be used for that language. For example, Mandarin Chinese
        is 'zh', not 'cmn', according to Unicode, and Malay is 'ms', not 'zsm'.

        This isn't a rule you'd want to follow in all cases -- for example, you may
        want to be able to specifically say that 'ms' (the Malay macrolanguage)
        contains both 'zsm' (Standard Malay) and 'id' (Indonesian). But applying
        this rule helps when interoperating with the Unicode CLDR.

        So, applying `prefer_macrolanguage` to a LanguageData object will
        return a new object, replacing the language with the macrolanguage if
        it is the dominant language within that macrolanguage. It will leave
        non-dominant languages that have macrolanguages alone.

        >>> LanguageData.parse('arb').prefer_macrolanguage()
        LanguageData(language='ar')

        >>> LanguageData.parse('cmn-Hant').prefer_macrolanguage()
        LanguageData(language='zh', script='Hant')

        >>> LanguageData.parse('yue-Hant').prefer_macrolanguage()
        LanguageData(language='yue', macrolanguage='zh', script='Hant')
        """
        language = self.language or 'und'
        if language in NORMALIZED_MACROLANGUAGES:
            return self.update_dict({
                'language': NORMALIZED_MACROLANGUAGES[language],
                'macrolanguage': None
            })
        else:
            return self

    @staticmethod
    def _filter_keys(d, keys):
        """
        Select a subset of keys from a dictionary.
        """
        return {key: d[key] for key in keys if key in d}

    def _filter_attributes(self, keyset):
        """
        Return a copy of this object with a subset of its attributes set.
        """
        filtered = self._filter_keys(self.to_dict(), keyset)
        return LanguageData(**filtered)

    def broaden(self):
        """
        Iterate through increasingly general versions of this parsed language tag.

        This isn't actually that useful for matching two arbitrary language tags
        against each other, but it is useful for matching them against a known
        standardized form, such as in the CLDR data.

        >>> for langdata in LanguageData.parse('nn-Latn-NO-x-thingy').broaden():
        ...     print(langdata)
        nn-Latn-NO-x-thingy
        nn-Latn-NO
        nn-Latn
        nn-NO
        nn
        no-Latn-NO
        no-Latn
        no-NO
        no
        und-Latn-NO
        und-Latn
        und-NO
        und
        """
        yield self
        for keyset in self.BROADER_KEYSETS:
            yield self._filter_attributes(keyset)

    def fill_likely_values(self):
        """
        The Unicode CLDR contains a "likelySubtags" data file, which can guess
        reasonable values for fields that are missing from a language tag.

        This is particularly useful for comparing, for example, "zh-Hant" and
        "zh-TW", two common language tags that say approximately the same thing
        via rather different information. (Using traditional Han characters is
        not the same as being in Taiwan, but each implies that the other is
        likely.)

        These implications are provided in the CLDR supplemental data, and are
        based on the likelihood of people using the language to transmit
        information on the Internet. (This is why the overall default is English,
        not Chinese.)

        >>> str(LanguageData.parse('zh-Hant').fill_likely_values())
        'zh-Hant-TW'
        >>> str(LanguageData.parse('zh-TW').fill_likely_values())
        'zh-Hant-TW'
        >>> str(LanguageData.parse('ja').fill_likely_values())
        'ja-Jpan-JP'
        >>> str(LanguageData.parse('pt').fill_likely_values())
        'pt-Latn-BR'
        >>> str(LanguageData.parse('und-Arab').fill_likely_values())
        'ar-Arab-EG'
        >>> str(LanguageData.parse('und-CH').fill_likely_values())
        'de-Latn-CH'
        >>> str(LanguageData().fill_likely_values())    # 'MURICA.
        'en-Latn-US'
        """
        for broader in self.broaden():
            tag = str(broader)
            if tag in LIKELY_SUBTAGS:
                result = LanguageData.parse(LIKELY_SUBTAGS[tag])
                return result.update(self)

        raise RuntimeError(
            "Couldn't fill in likely values. This represents a problem with "
            "langcodes.db.LIKELY_SUBTAGS."
        )

    def _searchable_form(self):
        """
        Convert a parsed language tag so that the information it contains is in
        the best form for looking up information in the CLDR.
        """
        return self._filter_attributes(
            {'macrolanguage', 'language', 'script', 'region'}
        ).simplify_script().prefer_macrolanguage()

    def match_score(self, supported):
        """
        Suppose that `self` is the language that the user desires, and
        `supported` is a language that is actually supported. This method
        returns a number from 0 to 100 indicating the strength of the match
        between them. This is not a symmetric relation.

        See :func:`tag_match_score` for a function that works on strings,
        instead of requiring you to instantiate LanguageData objects first.
        Further documentation and examples appear with that function.
        """
        if supported == self:
            return 100

        desired_complete = self.prefer_macrolanguage().fill_likely_values()
        supported_complete = supported.prefer_macrolanguage().fill_likely_values()
        desired_reduced = desired_complete._searchable_form()
        supported_reduced = supported_complete._searchable_form()

        # if the languages match after we normalize them, that's very good
        if desired_reduced == supported_reduced:
            return 99

        # CLDR doesn't tell us how to combine the data in 'parentLocales' with
        # that in 'languageMatching', so here's a heuristic that seems to fit.
        desired_tag = str(desired_reduced)
        supported_tag = str(supported_reduced)
        if PARENT_LOCALES.get(desired_tag) == supported_tag:
            return 98
        if PARENT_LOCALES.get(supported_tag) == desired_tag:
            return 97

        # Look for language pairs that are present in CLDR's 'languageMatching'.
        for keyset in self.MATCHABLE_KEYSETS:
            desired_filtered_tag = str(
                desired_complete._filter_attributes(keyset).simplify_script()
            )
            supported_filtered_tag = str(
                supported_complete._filter_attributes(keyset).simplify_script()
            )
            pair = (desired_filtered_tag, supported_filtered_tag)
            if pair in LANGUAGE_MATCHING:
                return LANGUAGE_MATCHING[pair]

        if desired_complete.language == supported_complete.language:
            if desired_complete.script == supported_complete.script:
                return 96
            # Implement these wildcard rules about Han scripts explicitly.
            elif desired_complete.script == 'Hans' and supported_complete.script == 'Hant':
                return 85
            elif desired_complete.script == 'Hant' and supported_complete.script == 'Hans':
                return 75
            else:
                # A low-ish score for incompatible scripts.
                return 20

        if desired_complete.macrolanguage or supported_complete.macrolanguage:
            # This rule isn't in the CLDR data, because they don't trust any
            # information about sub-languages of a macrolanguage.
            #
            # If the two language codes share a macrolanguage, we take half of
            # what their match value would be if the macrolanguage were a language.

            desired_macro = desired_complete
            supported_macro = supported_complete
            if desired_complete.macrolanguage:
                desired_macro = desired_macro.update_dict(
                    {'language': desired_complete.macrolanguage,
                     'macrolanguage': None}
                )
            if supported_complete.macrolanguage:
                supported_macro = supported_macro.update_dict(
                    {'language': supported_complete.macrolanguage,
                     'macrolanguage': None}
                )
            if desired_macro != desired_complete or supported_macro != supported_complete:
                print(desired_macro, desired_complete)
                print(supported_macro, supported_complete)
                #return desired_macro.match_score(supported_macro) // 2

        # There is nothing that matches.
        # CLDR would give a match value of 1 here, for reasons I suspect are
        # internal to their own software. Forget that. 0 should mean "no match".
        return 0

    # These methods help to show what the language tag means in natural
    # language. They actually apply the language-matching algorithm to find
    # the right language to name things in.

    def _get_name(self, attribute, language, min_score):
        assert attribute in self.ATTRIBUTES
        if isinstance(language, LanguageData):
            language = str(language)

        names = DB.names_for(attribute, getattr(self, attribute))
        names['und'] = getattr(self, attribute)
        return self._best_name(names, language, min_score)

    def _best_name(self, names, language, min_score):
        possible_languages = sorted(names.keys())
        target_language, score = best_match(language, possible_languages, min_score)
        return names[target_language]

    def language_name(self, language=DEFAULT_LANGUAGE, min_score=90):
        """
        Give the name of the language (and no other subtags) in a natural language.

        By default, things are named in English:

        >>> from pprint import pprint
        >>> LanguageData(language='fr').language_name()
        'French'

        But you can ask for language names in numerous other languages:

        >>> LanguageData(language='fr').language_name('fr')
        'français'

        Why does everyone get Slovak and Slovenian confused? Let's ask them.

        >>> LanguageData(language='sl').language_name('sl')
        'slovenščina'
        >>> LanguageData(language='sk').language_name('sk')
        'slovenčina'
        >>> LanguageData(language='sl').language_name('sk')
        'slovinčina'
        >>> LanguageData(language='sk').language_name('sl')
        'slovaščina'
        """
        return self._get_name('language', language, min_score)

    def script_name(self, language=DEFAULT_LANGUAGE, min_score=90):
        return self._get_name('script', language, min_score)

    def region_name(self, language=DEFAULT_LANGUAGE, min_score=90):
        return self._get_name('region', language, min_score)

    def variant_names(self, language=DEFAULT_LANGUAGE, min_score=90):
        names = []
        for variant in self.variants:
            var_names = DB.names_for('variant', variant)
            names.append(self._best_name(var_names, language, min_score))
        return names

    def describe(self, language=DEFAULT_LANGUAGE, min_score=90):
        """
        Return a dictionary that describes a given language tag in a specified
        natural language.

        See `language_name` and related methods for more specific versions of this.

        The desired `language` will in fact be matched against the available
        options using the matching technique that this module provides.  We can
        illustrate many aspects of this by asking for a description of Shavian
        script (a script devised by author George Bernard Shaw), and where you
        might find it, in various languages.

        >>> from pprint import pprint
        >>> pprint(LanguageData(script='Shaw').fill_likely_values().describe('en'))
        {'language': 'English', 'region': 'U.K.', 'script': 'Shavian'}

        >>> pprint(LanguageData(script='Shaw').fill_likely_values().describe('en-GB'))
        {'language': 'English', 'region': 'UK', 'script': 'Shavian'}

        >>> pprint(LanguageData(script='Shaw').fill_likely_values().describe('en-AU'))
        {'language': 'English', 'region': 'UK', 'script': 'Shavian'}

        >>> pprint(LanguageData(script='Shaw').fill_likely_values().describe('en-CA'))
        {'language': 'English', 'region': 'U.K.', 'script': 'Shavian'}

        >>> pprint(LanguageData(script='Shaw').fill_likely_values().describe('fr'))
        {'language': 'anglais', 'region': 'R.-U.', 'script': 'shavien'}

        >>> pprint(LanguageData(script='Shaw').fill_likely_values().describe('es'))
        {'language': 'inglés', 'region': 'Reino Unido', 'script': 'shaviano'}

        >>> pprint(LanguageData(script='Shaw').fill_likely_values().describe('pt'))
        {'language': 'inglês', 'region': 'GB', 'script': 'shaviano'}

        >>> pprint(LanguageData(script='Shaw').fill_likely_values().describe('uk'))
        {'language': 'англійська', 'region': 'Велика Британія', 'script': 'Шоу'}

        >>> pprint(LanguageData(script='Shaw').fill_likely_values().describe('arb'))
        {'language': 'الإنجليزية', 'region': 'المملكة المتحدة', 'script': 'الشواني'}

        >>> pprint(LanguageData(script='Shaw').fill_likely_values().describe('th'))
        {'language': 'อังกฤษ', 'region': 'สหราชอาณาจักร', 'script': 'ซอเวียน'}

        >>> pprint(LanguageData(script='Shaw').fill_likely_values().describe('zh-Hans'))
        {'language': '英文', 'region': '英国', 'script': '萧伯纳式文'}

        >>> pprint(LanguageData(script='Shaw').fill_likely_values().describe('zh-Hant'))
        {'language': '英文', 'region': '英國', 'script': '簫柏納字符'}

        >>> pprint(LanguageData(script='Shaw').fill_likely_values().describe('ja'))
        {'language': '英語', 'region': 'イギリス', 'script': 'ショー文字'}

        >>> # When we don't have a localization for the language, we fall back on
        >>> # 'und', which just shows the language codes.
        >>> pprint(LanguageData(script='Shaw').fill_likely_values().describe('lol'))
        {'language': 'en', 'region': 'GB', 'script': 'Shaw'}

        >>> # Wait, is that a real language?
        >>> pprint(LanguageData.parse('lol').fill_likely_values().describe())
        {'language': 'Mongo', 'region': 'Congo (DRC)', 'script': 'Latin'}
        """
        names = {}
        if self.language:
            names['language'] = self.language_name(language, min_score)
        if self.script:
            names['script'] = self.script_name(language, min_score)
        if self.region:
            names['region'] = self.region_name(language, min_score)
        if self.variants:
            names['variants'] = self.variant_names(language, min_score)
        return names


def standardize_tag(tag, macro=False):
    """
    Standardize a language tag:

    - Replace deprecated values with their updated versions (if those exist)
    - Remove script tags that are redundant with the language
    - If *macro* is True, use a macrolanguage to represent the most common
      standardized language within that macrolanguage. For example, 'cmn'
      (Mandarin) becomes 'zh' (Chinese), and 'arb' (Modern Standard Arabic)
      becomes 'ar' (Arabic).
    - Format the result according to the conventions of BCP 47

    Macrolanguage replacement is not required by BCP 47, but it is required
    by the Unicode CLDR.

    >>> standardize_tag('en_US')
    'en-US'

    >>> standardize_tag('en-Latn')
    'en'

    >>> standardize_tag('en-uk')
    'en-GB'

    >>> standardize_tag('arb-Arab', macro=True)
    'ar'

    >>> standardize_tag('sh-QU')
    'sr-Latn-EU'

    >>> standardize_tag('sgn-US')
    'ase'

    >>> standardize_tag('zh-cmn-hans-cn')
    'cmn-Hans-CN'

    >>> standardize_tag('zh-cmn-hans-cn', macro=True)
    'zh-Hans-CN'
    """
    langdata = LanguageData.parse(tag, normalize=True)
    if macro:
        langdata = langdata.prefer_macrolanguage()

    return langdata.simplify_script().to_tag()


_CACHE = {}


def tag_match_score(desired, supported):
    """
    Return a number from 0 to 100 indicating the strength of match between the
    language the user desires, D, and a supported language, S. The scale comes
    from CLDR data, but we've added some scale steps to deal with languages
    within macrolanguages.

    The results of tag_match_score are cached so that they'll be looked up
    more quickly in the future.

    A match strength of 100 indicates that the languages should be considered the
    same. Perhaps because they are the same.

    >>> tag_match_score('en', 'en')
    100

    >>> # Unspecified Norwegian means Bokmål in practice.
    >>> tag_match_score('no', 'nb')
    100

    >>> # Serbo-Croatian is a politically contentious idea, but in practice
    >>> # it's considered equivalent to Serbian in Latin characters.
    >>> tag_match_score('sh', 'sr-Latn')
    100

    A match strength of 99 indicates that the languages are the same after
    filling in likely values and normalizing. There may be situations in which
    the tags differ, but users are unlikely to be bothered. A machine learning
    algorithm expecting input in language S should do just fine in language D.

    >>> tag_match_score('en', 'en-US')
    99
    >>> tag_match_score('zh-Hant', 'zh-TW')
    99
    >>> tag_match_score('ru-Cyrl', 'ru')
    99

    A match strength of 97 or 98 means that the language tags are different,
    but are culturally similar enough that they should be interchangeable in
    most contexts. (The CLDR provides the data about related locales, but
    doesn't assign it a match strength. It uses hacky wildcard-based rules for
    this purpose instead. The end result is very similar.)

    >>> tag_match_score('en-AU', 'en-GB')   # Australian English is similar to British
    98
    >>> tag_match_score('en-IN', 'en-GB')   # Indian English is also similar to British
    98
    >>> # It might be slightly more unexpected to ask for British usage and get
    >>> # Indian usage than the other way around.
    >>> tag_match_score('en-GB', 'en-IN')
    97
    >>> tag_match_score('es-PR', 'es-419')  # Peruvian Spanish is Latin American Spanish
    98

    A match strength of 96 means that the tags indicate a regional difference.
    Users may notice some unexpected usage, and NLP algorithms that expect one
    language may occasionally trip up on the other.

    >>> # European Portuguese is a bit different from the Brazilian most common dialect
    >>> tag_match_score('pt', 'pt-PT')
    96
    >>> # UK and US English are also a bit different
    >>> tag_match_score('en-GB', 'en-US')
    96
    >>> # Swiss German speakers will understand standardized German
    >>> tag_match_score('gsw', 'de')
    96
    >>> # Most German speakers will think Swiss German is a foreign language
    >>> tag_match_score('de', 'gsw')
    0

    A match strength of 90 represents languages with a considerable amount of
    overlap and some amount of mutual intelligibility. People will probably be
    able to handle the difference with a bit of discomfort.

    Algorithms may have more trouble, but you could probably train your NLP on
    _both_ languages without any problems. Below this match strength, though,
    don't expect algorithms to be compatible.

    >>> tag_match_score('no', 'da')  # Norwegian Bokmål is like Danish
    90
    >>> tag_match_score('id', 'ms')  # Indonesian is like Malay
    90
    >>> # Serbian language users will usually understand Serbian in its other script.
    >>> tag_match_score('sr-Latn', 'sr-Cyrl')
    90

    A match strength of 85 indicates a script that well-educated users of the
    desired language will understand, but they won't necessarily be happy with
    it. In particular, those who write in Simplified Chinese can often
    understand the Traditional script.

    >>> tag_match_score('zh-Hans', 'zh-Hant')
    85
    >>> tag_match_score('zh-CN', 'zh-HK')
    85

    A match strength of 75 indicates a script that users of the desired language
    are passingly familiar with, but would have to go out of their way to learn.
    Those who write in Traditional Chinese are less familiar with the Simplified
    script than the other way around.

    >>> tag_match_score('zh-Hant', 'zh-Hans')
    75
    >>> tag_match_score('zh-HK', 'zh-CN')
    75

    Checking the macrolanguage is an extension that we added. The following
    match strengths from 37 to 50 come from our interpretation of how to handle
    macrolanguages, as opposed to the CLDR's position of wishing they would go
    away.

    A match strength of 50 means that the languages are different sub-languages of
    a macrolanguage. Their mutual intelligibility will vary considerably based on
    the circumstances.

    >>> # Gan is considered a kind of Chinese, but it's fairly different from Mandarin.
    >>> tag_match_score('gan', 'zh')
    50

    A match strength of 35 to 49 has one of the differences described above as well
    as being different sub-languages of a macrolanguage.

    >>> # Hong Kong uses traditional Chinese characters, but it may contain
    >>> # Cantonese-specific expressions that are gibberish in Mandarin,
    >>> # hindering intelligibility.
    >>> tag_match_score('zh-Hant', 'yue-HK')
    48
    >>> # Mainland Chinese is actually a poor match for Hong Kong Cantonese.
    >>> tag_match_score('yue-HK', 'zh-CN')
    37

    A match strength of 20 indicates that the script that's supported is a
    different one than desired. This is usually a big problem, because most
    people only read their native language in one script, and in another script
    it would be gibberish to them. I think CLDR is assuming you've got a good
    reason to support the script you support.

    >>> # Japanese may be understandable when romanized.
    >>> tag_match_score('ja', 'ja-Latn-US-hepburn')
    20
    >>> # You can read the Shavian script, right?
    >>> tag_match_score('en', 'en-Shaw')
    20

    A match strength of 10 is a last resort that might be better than matching
    nothing. In most cases, it indicates that numerous speakers of language D
    happen to understand language S, despite that there might be no connection
    between the languages.

    >>> tag_match_score('ta', 'en')   # Many computer-using Tamil speakers also know English.
    10
    >>> tag_match_score('af', 'nl')   # Afrikaans and Dutch at least share history.
    10
    >>> tag_match_score('eu', 'es')   # Basque speakers may grudgingly read Spanish.
    10

    Otherwise, the match value is 0.

    >>> tag_match_score('ar', 'fa')   # Arabic and Persian (Farsi) do not match.
    0
    >>> tag_match_score('en', 'ta')   # English speakers generally do not know Tamil.
    0
    """
    if (desired, supported) in _CACHE:
        return _CACHE[desired, supported]

    desired_ld = LanguageData.parse(desired)
    supported_ld = LanguageData.parse(supported)
    score = desired_ld.match_score(supported_ld)
    _CACHE[desired, supported] = score
    return score


def best_match(desired_language, supported_languages, min_score=90):
    """
    You have software that supports any of the `supported_languages`. You want
    to use `desired_language`. This function lets you choose the right language,
    even if there isn't an exact match.

    Returns:

    - The best-matching language code, which will be one of the
      `supported_languages` or 'und'
    - The match strength, from 0 to 100

    `min_score` sets the minimum score that will be allowed to match. If all
    the scores are less than `min_score`, the result will be 'und' with a
    strength of 0.

    When there is a tie for the best matching language, the first one in the
    tie will be used.

    Setting `min_score` lower will enable more things to match, at the cost of
    possibly mis-handling data or upsetting users. Read the documentation for
    :func:`tag_match_score` to understand what the numbers mean.

    >>> best_match('fr', ['de', 'en', 'fr'])
    ('fr', 100)
    >>> best_match('sh', ['hr', 'bs', 'sr-Latn', 'sr-Cyrl'])
    ('sr-Latn', 100)
    >>> best_match('zh-CN', ['zh-Hant', 'zh-Hans', 'gan', 'nan'])
    ('zh-Hans', 99)
    >>> best_match('zh-CN', ['cmn-Hant', 'cmn-Hans', 'gan', 'nan'])
    ('cmn-Hans', 99)
    >>> best_match('pt', ['pt-BR', 'pt-PT'])
    ('pt-BR', 99)
    >>> best_match('en-AU', ['en-GB', 'en-US'])
    ('en-GB', 98)
    >>> best_match('es-MX', ['es-ES', 'es-419', 'en-US'])
    ('es-419', 98)
    >>> best_match('es-MX', ['es-PU', 'es-AR', 'es-PY'])
    ('es-PU', 96)
    >>> best_match('es-MX', ['es-AR', 'es-PU', 'es-PY'])
    ('es-AR', 96)
    >>> best_match('id', ['zsm', 'mhp'])
    ('zsm', 90)
    >>> best_match('eu', ['el', 'en', 'es'], min_score=10)
    ('es', 10)
    >>> best_match('eu', ['el', 'en', 'es'])
    ('und', 0)
    """
    match_scores = [
        (supported, tag_match_score(desired_language, supported))
        for supported in supported_languages
    ]
    match_scores = [
        (supported, score) for (supported, score) in match_scores
        if score >= min_score
    ] + [('und', 0)]

    match_scores.sort(key=lambda item: -item[1])
    return match_scores[0]


def normalize_language_tag(tag, macrolanguage=True):
    """
    Converts a language tag to a standardized form. This includes making sure
    to use the shortest form of the language code, removing the script subtag
    if it's obvious, and using the conventional capitalization.

    If the 'macrolanguage' option is True (the default), it will follow the
    CLDR recommendation of using the codes for macrolanguages in place of the
    more specific code for the predominant language within that macrolanguage.

    >>> normalize_language_tag('eng')
    'en'
    >>> normalize_language_tag('eng-UK')
    'en-GB'
    >>> normalize_language_tag('zsm')
    'ms'
    >>> normalize_language_tag('arb-Arab')
    'ar'
    >>> normalize_language_tag('ja-latn-hepburn')
    'ja-Latn-hepburn'
    >>> normalize_language_tag('spa-latn-mx')
    'es-MX'

    If the tag can't be parsed according to BCP 47, this will raise a
    LanguageTagError (a subclass of ValueError):

    >>> normalize_language_tag('spa-mx-latn')
    Traceback (most recent call last):
        ...
    langcodes.tag_parser.LanguageTagError: This script subtag, 'latn', is out of place. Expected variant, extension, or end of string.
    """
    parsed = LanguageData.parse(tag)
    if macrolanguage:
        parsed = parsed.prefer_macrolanguage()
    return str(parsed.simplify_script())

