"""
langcodes knows what languages are. It knows the standardized codes that
refer to them, such as `en` for English, `es` for Spanish and `hi` for Hindi.
Often, it knows what these languages are called *in* a language, and that
language doesn't have to be English.

See README.md for the main documentation, or read it on GitHub at
https://github.com/LuminosoInsight/langcodes/ . For more specific documentation
on the functions in langcodes, scroll down and read the docstrings.
"""
from .tag_parser import parse_tag
from .db import LanguageDB
from .util import data_filename

# When we're getting natural language information *about* languages, it's in
# U.S. English if you don't specify the language.
DEFAULT_LANGUAGE = 'en-US'

# Load the SQLite database that contains the data we need about languages.
DB = LanguageDB(data_filename('subtags.db'))


class AmbiguousError(LookupError):
    """
    Raised when there is more than one subtag matching a given natural
    language name.
    """
    pass


class LanguageData:
    """
    The LanguageData class defines the results of parsing a language tag.
    LanguageData objects have the following attributes, any of which may be
    unspecified (in which case their value is None):

    - *language*: the code for the language itself.
    - *macrolanguage*: a code for a broader language that contains that language.
    - *script*: the 4-letter code for the writing system being used.
    - *region*: the 2-letter or 3-digit code for the country or similar region
      whose usage of the language appears in this text.
    - *extlangs*: a list of more specific language codes that follow the language
      code. (This is allowed by the language code syntax, but deprecated.)
    - *variants*: codes for specific variations of language usage that aren't
      covered by the *script* or *region* codes.
    - *extensions*: information that's attached to the language code for use in
      some specific system, such as Unicode collation orders.
    - *private*: a code starting with `x-` that has no defined meaning.

    The `LanguageData.get` method converts a string to a LanguageData instance.
    It's also available at the top level of this module as the `get` function.
    """

    ATTRIBUTES = ['language', 'macrolanguage', 'extlangs', 'script', 'region',
                  'variants', 'extensions', 'private']

    # When looking up "likely subtags" data, we try looking up the data for
    # increasingly less specific versions of the language code.
    BROADER_KEYSETS = [
        {'language', 'script', 'region'},
        {'language', 'region'},
        {'language', 'script'},
        {'language'},
        {'macrolanguage', 'script', 'region'},
        {'macrolanguage', 'region'},
        {'macrolanguage', 'script'},
        {'macrolanguage'},
        {'script'},
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
        """
        Create a LanguageData object by giving any subset of its attributes.
        """
        self.language = language or macrolanguage
        self.macrolanguage = macrolanguage or language
        self.extlangs = extlangs
        self.script = script
        self.region = region
        self.variants = variants
        self.extensions = extensions
        self.private = private

    @staticmethod
    def get(tag: str, normalize=True) -> 'LanguageData':
        """
        Create a LanguageData object from a language tag string.

        If normalize=True, non-standard or overlong tags will be replaced as
        they're interpreted. This is recommended.

        Here are several examples of language codes, which are also test cases.
        Most language codes are straightforward, but these examples will get
        pretty obscure toward the end.

        >>> LanguageData.get('en-US')
        LanguageData(language='en', region='US')

        >>> LanguageData.get('zh-Hant')
        LanguageData(language='zh', script='Hant')

        >>> LanguageData.get('und')
        LanguageData()

        The non-code 'root' is sometimes used to represent the lack of any
        language information, similar to 'und'.

        >>> LanguageData.get('root')
        LanguageData()

        By default, getting a LanguageData object will automatically convert
        deprecated tags:

        >>> LanguageData.get('iw')
        LanguageData(language='he')

        >>> LanguageData.get('in')
        LanguageData(language='id', macrolanguage='ms')

        One type of deprecated tag that should be replaced is for sign
        languages, which used to all be coded as regional variants of a
        fictitious global sign language called 'sgn'. Of course, there is no
        global sign language, so sign languages now have their own language
        codes.

        >>> LanguageData.get('sgn-US')
        LanguageData(language='ase')

        >>> LanguageData.get('sgn-US', normalize=False)
        LanguageData(language='sgn', region='US')

        Some macrolanguages have been divided into language codes for the
        specific mutually-unintelligible languages they contain. Most
        internationalization code continues to use the macrolanguage, such as
        'zh' for Chinese, but data projects such as Wiktionary and Ethnologue
        want to be more specific, so they use the codes that distinguish
        languages, such as 'cmn' for Mandarin and 'yue' for Cantonese.

        For this reason, LanguageData objects keep track of both the
        macrolanguage and the specific language when they're allowed to
        normalize the input.

        >>> LanguageData.get('zh-cmn-Hant')  # promote extlangs to languages
        LanguageData(language='cmn', macrolanguage='zh', script='Hant')

        >>> LanguageData.get('zh-cmn-Hant', normalize=False)
        LanguageData(language='zh', extlangs=['cmn'], script='Hant')

        'en-gb-oed' is a tag that's grandfathered into the standard because it
        has been used to mean "spell-check this with Oxford English Dictionary
        spelling", but that tag has the wrong shape. We interpret this as the
        new standardized tag 'en-gb-oxendict', unless asked not to normalize.

        >>> LanguageData.get('en-gb-oed')
        LanguageData(language='en', region='GB', variants=['oxendict'])

        >>> LanguageData.get('en-gb-oed', normalize=False)
        LanguageData(language='en-gb-oed')

        'zh-min-nan' is another oddly-formed tag, used to represent the
        Southern Min language, which includes Taiwanese as a regional form. It
        now has its own language code.

        >>> LanguageData.get('zh-min-nan')
        LanguageData(language='nan', macrolanguage='zh')

        There's not much we can do with the vague tag 'zh-min':

        >>> LanguageData.get('zh-min')
        LanguageData(language='zh-min')

        Occasionally Wiktionary will use 'extlang' tags in strange ways, such
        as using the tag 'und-ibe' for some unspecified Iberian language.

        >>> LanguageData.get('und-ibe')
        LanguageData(extlangs=['ibe'])

        Here's an example of replacing multiple deprecated tags.

        The language tag 'sh' (Serbo-Croatian) ended up being politically
        problematic, and different standards took different steps to address
        this. The IANA made it into a macrolanguage that contains 'sr', 'hr',
        and 'bs'. Unicode further decided that it's a legacy tag that should
        be interpreted as 'sr-Latn', which the language matching rules say
        is mutually intelligible with all those languages.

        We complicate the example by adding on the region tag 'QU', an old
        provisional tag for the European Union, which is now standardized as
        'EU'.

        >>> LanguageData.get('sh-QU')
        LanguageData(language='sr', macrolanguage='sh', script='Latn', region='EU')
        """
        data = {}
        # if the complete tag appears as something to normalize, do the
        # normalization right away. Smash case when checking, because the
        # case normalization that comes from parse_tag() hasn't been applied
        # yet.
        if normalize and tag.lower() in DB.normalized_languages:
            tag = DB.normalized_languages[tag.lower()]

        components = parse_tag(tag)

        for typ, value in components:
            if typ == 'extlang' and normalize and 'language' in data:
                # smash extlangs when possible
                minitag = '%s-%s' % (data['language'], value)
                if minitag in DB.normalized_languages:
                    norm = DB.normalized_languages[minitag]
                    data.update(
                        LanguageData.get(norm, normalize).to_dict()
                    )
                else:
                    data.setdefault('extlangs', []).append(value)
            elif typ in {'extlang', 'variant', 'extension'}:
                data.setdefault(typ + 's', []).append(value)
            elif typ == 'language':
                if value == 'und':
                    pass
                elif normalize and value in DB.normalized_languages:
                    replacement = DB.normalized_languages[value]
                    # parse the replacement if necessary -- this helps with
                    # Serbian and Moldovan
                    data.update(
                        LanguageData.get(replacement, normalize).to_dict()
                    )
                else:
                    data['language'] = value
                    if value in DB.macrolanguages:
                        data['macrolanguage'] = DB.macrolanguages[value]
            elif typ == 'region':
                if normalize and value in DB.normalized_regions:
                    data['region'] = DB.normalized_regions[value]
                else:
                    data['region'] = value
            elif typ == 'grandfathered':
                # If we got here, we got a grandfathered tag but we were asked
                # not to normalize it, or the DB doesn't know how to normalize
                # it. The best we can do is set the entire tag as the language.
                data['language'] = value
            else:
                data[typ] = value

        return LanguageData(**data)

    def to_tag(self) -> str:
        """
        Convert a LanguageData back to a standard language tag, as a string.
        This is also the str() representation of a LanguageData object.

        >>> LanguageData(language='en', region='GB').to_tag()
        'en-GB'

        >>> LanguageData(language='yue', macrolanguage='zh', script='Hant',
        ...              region='HK').to_tag()
        'yue-Hant-HK'

        >>> LanguageData(script='Arab').to_tag()
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

    def simplify_script(self) -> 'LanguageData':
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
            if DB.default_scripts.get(self.language) == self.script:
                return self.update_dict({'script': None})

        return self

    def assume_script(self) -> 'LanguageData':
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
                return self.update_dict({'script': DB.default_scripts[self.language]})
            except KeyError:
                return self
        else:
            return self

    def prefer_macrolanguage(self) -> 'LanguageData':
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

        >>> LanguageData.get('arb').prefer_macrolanguage()
        LanguageData(language='ar')

        >>> LanguageData.get('cmn-Hant').prefer_macrolanguage()
        LanguageData(language='zh', script='Hant')

        >>> LanguageData.get('yue-Hant').prefer_macrolanguage()
        LanguageData(language='yue', macrolanguage='zh', script='Hant')
        """
        language = self.language or 'und'
        if language in DB.normalized_macrolanguages:
            return self.update_dict({
                'language': DB.normalized_macrolanguages[language],
                'macrolanguage': None
            })
        else:
            return self

    def broaden(self) -> 'Iterable[LanguageData]':
        """
        Iterate through increasingly general versions of this parsed language tag.

        This isn't actually that useful for matching two arbitrary language tags
        against each other, but it is useful for matching them against a known
        standardized form, such as in the CLDR data.

        The list of broader versions to try appears in UTR 35, section 4.3,
        "Likely Subtags".

        >>> for langdata in LanguageData.get('nn-Latn-NO-x-thingy').broaden():
        ...     print(langdata)
        nn-Latn-NO-x-thingy
        nn-Latn-NO
        nn-NO
        nn-Latn
        nn
        no-Latn-NO
        no-NO
        no-Latn
        no
        und-Latn
        und
        """
        yield self
        for keyset in self.BROADER_KEYSETS:
            yield self._filter_attributes(keyset)

    def fill_likely_values(self) -> 'LanguageData':
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

        >>> str(LanguageData.get('zh-Hant').fill_likely_values())
        'zh-Hant-TW'
        >>> str(LanguageData.get('zh-TW').fill_likely_values())
        'zh-Hant-TW'
        >>> str(LanguageData.get('ja').fill_likely_values())
        'ja-Jpan-JP'
        >>> str(LanguageData.get('pt').fill_likely_values())
        'pt-Latn-BR'
        >>> str(LanguageData.get('und-Arab').fill_likely_values())
        'ar-Arab-EG'
        >>> str(LanguageData.get('und-CH').fill_likely_values())
        'de-Latn-CH'
        >>> str(LanguageData().fill_likely_values())    # 'MURICA.
        'en-Latn-US'
        >>> str(LanguageData.get('und-ibe').fill_likely_values())
        'en-ibe-Latn-US'
        """
        for broader in self.broaden():
            tag = str(broader)
            if tag in DB.likely_subtags:
                result = LanguageData.get(DB.likely_subtags[tag])
                return result.update(self)

        raise RuntimeError(
            "Couldn't fill in likely values. This represents a problem with "
            "DB.likely_subtags."
        )

    def match_score(self, supported: 'LanguageData') -> int:
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

        # CLDR suggests using 'parentLocales' with 'languageMatching', but
        # doesn't assign numerical values to parent locales. Here are some
        # numbers that seem to match the intent.
        desired_tag = str(desired_reduced)
        supported_tag = str(supported_reduced)
        if DB.parent_locales.get(desired_tag) == supported_tag:
            return 99
        if DB.parent_locales.get(supported_tag) == desired_tag:
            return 98

        # Look for language pairs that are present in CLDR's 'languageMatching'.
        for keyset in self.MATCHABLE_KEYSETS:
            desired_filtered_tag = str(
                desired_complete._filter_attributes(keyset).simplify_script()
            )
            supported_filtered_tag = str(
                supported_complete._filter_attributes(keyset).simplify_script()
            )
            pair = (desired_filtered_tag, supported_filtered_tag)
            if pair in DB.language_matching:
                return DB.language_matching[pair]

        if desired_complete.language == supported_complete.language:
            # Partial wildcard rules from CLDR's 'languageMatching'. I'm not
            # trying to interpret the ugly format they're written in, so I'm
            # just reimplementing them. There are only eight of these rules
            # anyway.

            if desired_complete.script == supported_complete.script:
                if desired_complete.language == 'en' and desired_complete.region == 'US':
                    return 97
                elif desired_complete.language == 'es' and desired_complete.region == 'ES':
                    return 97
                elif desired_complete.language == 'es' and desired_complete.region == '419':
                    return 99
                elif desired_complete.language == 'es':
                    return 98
                else:
                    return 96
            elif desired_complete.script == 'Hans' and supported_complete.script == 'Hant':
                return 85
            elif desired_complete.script == 'Hant' and supported_complete.script == 'Hans':
                return 75
            else:
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
                return desired_macro.match_score(supported_macro) // 2

        # There is nothing that matches.
        # CLDR would give a match value of 1 here, for reasons I suspect are
        # internal to their own software. Forget that. 0 should mean "no match".
        return 0

    # These methods help to show what the language tag means in natural
    # language. They actually apply the language-matching algorithm to find
    # the right language to name things in.

    def _get_name(self, attribute: str, language, min_score: int):
        assert attribute in self.ATTRIBUTES
        if isinstance(language, LanguageData):
            language = str(language)

        names = DB.names_for(attribute, getattr(self, attribute))
        names['und'] = getattr(self, attribute)
        return self._best_name(names, language, min_score)

    def _best_name(self, names: dict, language: str, min_score: int):
        possible_languages = sorted(names.keys())
        target_language, score = best_match(language, possible_languages, min_score)
        return names[target_language]

    def language_name(self, language=DEFAULT_LANGUAGE, min_score: int=90) -> str:
        """
        Give the name of the language (not the entire tag, just the language part)
        in a natural language. The target language can be given as a string or
        another LanguageData object.

        By default, things are named in English:

        >>> LanguageData.get('fr').language_name()
        'French'
        >>> LanguageData.get('el').language_name()
        'Greek'

        But you can ask for language names in numerous other languages:

        >>> LanguageData.get('fr').language_name('fr')
        'français'
        >>> LanguageData.get('el').language_name('fr')
        'grec'

        Why does everyone get Slovak and Slovenian confused? Let's ask them.

        >>> LanguageData.get('sl').language_name('sl')
        'slovenščina'
        >>> LanguageData.get('sk').language_name('sk')
        'slovenčina'
        >>> LanguageData.get('sl').language_name('sk')
        'slovinčina'
        >>> LanguageData.get('sk').language_name('sl')
        'slovaščina'
        """
        return self._get_name('language', language, min_score)

    def autonym(self) -> str:
        """
        Give the name of this language *in* this language.

        >>> LanguageData.get('fr').autonym()
        'français'
        >>> LanguageData.get('es').autonym()
        'español'
        >>> LanguageData.get('ja').autonym()
        '日本語'

        This doesn't give the name of the region or script, but in one case,
        you can get the autonym in two different scripts:

        >>> LanguageData.get('sr-Latn').autonym()
        'srpski'
        >>> LanguageData.get('sr-Cyrl').autonym()
        'Српски'

        This only works for language codes that CLDR has locale data for. You
        can't ask for the autonym of 'ja-Latn' and get 'nihongo'.
        """
        return self.language_name(language=self, min_score=10)

    def script_name(self, language=DEFAULT_LANGUAGE, min_score: int=90) -> str:
        """
        Describe the script part of the language tag in a natural language.
        """
        return self._get_name('script', language, min_score)

    def region_name(self, language=DEFAULT_LANGUAGE, min_score: int=90) -> str:
        """
        Describe the region part of the language tag in a natural language.
        """
        return self._get_name('region', language, min_score)

    def variant_names(self, language=DEFAULT_LANGUAGE, min_score: int=90) -> list:
        """
        Describe each of the variant parts of the language tag in a natural
        language.
        """
        names = []
        for variant in self.variants:
            var_names = DB.names_for('variant', variant)
            names.append(self._best_name(var_names, language, min_score))
        return names

    def describe(self, language=DEFAULT_LANGUAGE, min_score: int=90) -> dict:
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
        >>> shaw = LanguageData(script='Shaw').fill_likely_values()
        >>> pprint(shaw.describe('en'))
        {'language': 'English', 'region': 'United Kingdom', 'script': 'Shavian'}

        >>> pprint(shaw.describe('fr'))
        {'language': 'anglais', 'region': 'Royaume-Uni', 'script': 'shavien'}

        >>> pprint(shaw.describe('es'))
        {'language': 'inglés', 'region': 'Reino Unido', 'script': 'shaviano'}

        >>> pprint(shaw.describe('pt'))
        {'language': 'inglês', 'region': 'Reino Unido', 'script': 'shaviano'}

        >>> pprint(shaw.describe('uk'))
        {'language': 'англійська', 'region': 'Велика Британія', 'script': 'Шоу'}

        >>> pprint(shaw.describe('arb'))
        {'language': 'الإنجليزية', 'region': 'المملكة المتحدة', 'script': 'الشواني'}

        >>> pprint(shaw.describe('th'))
        {'language': 'อังกฤษ', 'region': 'สหราชอาณาจักร', 'script': 'ซอเวียน'}

        >>> pprint(shaw.describe('zh-Hans'))
        {'language': '英文', 'region': '英国', 'script': '萧伯纳式文'}

        >>> pprint(shaw.describe('zh-Hant'))
        {'language': '英文', 'region': '英國', 'script': '簫柏納字符'}

        >>> pprint(shaw.describe('ja'))
        {'language': '英語', 'region': 'イギリス', 'script': 'ショー文字'}

        When we don't have a localization for the language, we fall back on
        'und', which just shows the language codes.

        >>> pprint(shaw.describe('lol'))
        {'language': 'en', 'region': 'GB', 'script': 'Shaw'}

        Wait, is that a real language?

        >>> pprint(LanguageData.get('lol').fill_likely_values().describe())
        {'language': 'Mongo', 'region': 'Congo - Kinshasa', 'script': 'Latin'}

        Sometimes the normalized and un-normalized versions of a language code
        have different descriptions:

        >>> LanguageData.get('mo')
        LanguageData(language='ro', region='MD')

        >>> pprint(LanguageData.get('mo').describe())
        {'language': 'Romanian', 'region': 'Moldova'}

        >>> pprint(LanguageData.get('mo', normalize=False).describe())
        {'language': 'Moldavian'}
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

    @staticmethod
    def find_name(tagtype: str, name: str, language: {str, 'LanguageData'}):
        """
        Find the subtag of a particular `tagtype` that has the given `name`.

        This is not a particularly powerful full-text search. It ignores case, but
        otherwise it expects the name to appear exactly the way it does in one of
        the databases that langcodes uses. If the exact name isn't found, you get a
        LookupError. If more than one subtag is found with the same name, you get
        an AmbiguousError.

        The `language` parameter is the language code or LanguageData object
        representing the language that you're providing the name in.

        >>> LanguageData.find_name('language', 'francés', 'es')
        LanguageData(language='fr')

        >>> LanguageData.find_name('region', 'United Kingdom', LanguageData.get('en'))
        LanguageData(region='GB')

        >>> LanguageData.find_name('script', 'Arabic', 'en')
        LanguageData(script='Arab')

        >>> LanguageData.find_name('language', 'norsk bokmål', 'no')
        LanguageData(language='nb')

        >>> LanguageData.find_name('language', 'norsk bokmal', 'no')
        Traceback (most recent call last):
            ...
        LookupError: Can't find any language named 'norsk bokmal'
        """
        und = LanguageData()
        english = LanguageData(language='en')

        options = DB.lookup_name_in_any_language(tagtype, name)
        if isinstance(language, LanguageData):
            target_language = language
        else:
            target_language = LanguageData.get(language)
        best_options = []
        best_match_score = 1

        for subtag, langcode in options:
            data_language = LanguageData.get(langcode)
            if data_language == und:
                # We don't want to match the language codes themselves.
                continue

            score = target_language.match_score(LanguageData.get(langcode))

            # Languages are often named in English, even when speaking in
            # other languages
            if data_language == english:
                score = 1

            # semi-secret trick: if you just want to match this name in whatever
            # language it's in, use 'und' as the language. This isn't in the
            # docstring because it's possibly a bad idea and possibly subject to
            # change.
            if target_language == und:
                score = 100

            if score > best_match_score:
                best_match_score = score
                best_options = [subtag]
            elif score == best_match_score:
                best_options.append(subtag)

        if len(best_options) == 0:
            raise LookupError(
                "Can't find any %s named %r" % (tagtype, name)
            )
        else:
            # If there are still multiple options, get the most specific one
            best = max(best_options, key=lambda item: item.count('-'))
            data = {tagtype: best}
            return LanguageData(**data)

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

    def update(self, other: 'LanguageData') -> 'LanguageData':
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

    def update_dict(self, newdata: dict) -> 'LanguageData':
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
    def _filter_keys(d: dict, keys: set) -> dict:
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

    def _searchable_form(self) -> 'LanguageData':
        """
        Convert a parsed language tag so that the information it contains is in
        the best form for looking up information in the CLDR.
        """
        return self._filter_attributes(
            {'macrolanguage', 'language', 'script', 'region'}
        ).simplify_script().prefer_macrolanguage()

    def __eq__(self, other):
        if not isinstance(other, LanguageData):
            return False
        return self.to_dict() == other.to_dict()

    def __getitem__(self, key):
        if key in self.ATTRIBUTES:
            return getattr(self, key)
        else:
            raise KeyError(key)

    def __contains__(self, key):
        return key in self.ATTRIBUTES and getattr(self, key)

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


# Make the get() and find_name() functions available at the top level
get = LanguageData.get
find_name = LanguageData.find_name


def standardize_tag(tag: str, macro: bool=False) -> str:
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

    >>> standardize_tag('eng')
    'en'

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

    >>> standardize_tag('zsm', macro=True)
    'ms'

    >>> standardize_tag('ja-latn-hepburn')
    'ja-Latn-hepburn'

    >>> standardize_tag('spa-latn-mx')
    'es-MX'

    If the tag can't be parsed according to BCP 47, this will raise a
    LanguageTagError (a subclass of ValueError):

    >>> standardize_tag('spa-mx-latn')
    Traceback (most recent call last):
        ...
    langcodes.tag_parser.LanguageTagError: This script subtag, 'latn', is out of place. Expected variant, extension, or end of string.
    """
    langdata = LanguageData.get(tag, normalize=True)
    if macro:
        langdata = langdata.prefer_macrolanguage()

    return langdata.simplify_script().to_tag()


_CACHE = {}


def tag_match_score(desired: str, supported: str) -> int:
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

    >>> tag_match_score('en-AU', 'en-GB')   # Australian English is similar to British
    99
    >>> tag_match_score('en-IN', 'en-GB')   # Indian English is also similar to British
    99
    >>> tag_match_score('es-PR', 'es-419')  # Peruvian Spanish is Latin American Spanish
    99

    A match strength of 97 or 98 means that the language tags are different,
    but are culturally similar enough that they should be interchangeable in
    most contexts. (The CLDR provides the data about related locales, but
    doesn't assign it a match strength. It uses hacky wildcard-based rules for
    this purpose instead. The end result is very similar.)

    A match strength of 96 to 98 indicates a regional difference. At a score of
    98, the regions are very similar in their language usage, and the language
    should be interchangeable in most contexts. At a score of 96, users may
    notice some unexpected usage, and NLP algorithms that expect one language
    variant may occasionally trip up on the other.

    >>> # It might be slightly more unexpected to ask for British usage and get
    >>> # Indian usage than the other way around.
    >>> tag_match_score('en-GB', 'en-IN')
    98

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

    desired_ld = LanguageData.get(desired)
    supported_ld = LanguageData.get(supported)
    score = desired_ld.match_score(supported_ld)
    _CACHE[desired, supported] = score
    return score


def best_match(desired_language: str, supported_languages: list,
               min_score: int=90) -> (str, int):
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
    ('en-GB', 99)
    >>> best_match('es-MX', ['es-ES', 'es-419', 'en-US'])
    ('es-419', 99)
    >>> best_match('es-MX', ['es-PU', 'es-AR', 'es-PY'])
    ('es-PU', 98)
    >>> best_match('es-MX', ['es-AR', 'es-PU', 'es-PY'])
    ('es-AR', 98)
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
