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
from .db import DB
from .distance import raw_distance
import warnings

# When we're getting natural language information *about* languages, it's in
# U.S. English if you don't specify the language.
DEFAULT_LANGUAGE = 'en-US'


class Language:
    """
    The Language class defines the results of parsing a language tag.
    Language objects have the following attributes, any of which may be
    unspecified (in which case their value is None):

    - *language*: the code for the language itself.
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

    The `Language.get` method converts a string to a Language instance.
    It's also available at the top level of this module as the `get` function.
    """

    ATTRIBUTES = ['language', 'extlangs', 'script', 'region',
                  'variants', 'extensions', 'private']

    # When looking up "likely subtags" data, we try looking up the data for
    # increasingly less specific versions of the language code.
    BROADER_KEYSETS = [
        {'language', 'script', 'region'},
        {'language', 'region'},
        {'language', 'script'},
        {'language'},
        {'script'},
        {}
    ]

    MATCHABLE_KEYSETS = [
        {'language', 'script', 'region'},
        {'language', 'script'},
        {'language'},
    ]

    # Values cached at the class level
    _INSTANCES = {}
    _PARSE_CACHE = {}

    def __init__(self, language=None, extlangs=None, script=None,
                 region=None, variants=None, extensions=None, private=None):
        """
        The constructor for Language objects.

        It's inefficient to call this directly, because it can't return
        an existing instance. Instead, call Language.make(), which
        has the same signature.
        """
        self.language = language
        self.extlangs = extlangs
        self.script = script
        self.region = region
        self.variants = variants
        self.extensions = extensions
        self.private = private

        # Cached values
        self._simplified = None
        self._searchable = None
        self._matchable_tags = None
        self._broader = None
        self._assumed = None
        self._filled = None
        self._macrolanguage = None
        self._str_tag = None
        self._dict = None

        # Make sure the str_tag value is cached
        self.to_tag()

    @classmethod
    def make(cls, language=None, extlangs=None, script=None,
             region=None, variants=None, extensions=None, private=None):
        """
        Create a Language object by giving any subset of its attributes.

        If this value has been created before, return the existing value.
        """
        values = (language, tuple(extlangs or ()), script, region,
                  tuple(variants or ()), tuple(extensions or ()), private)
        if values in cls._INSTANCES:
            return cls._INSTANCES[values]

        instance = cls(
            language=language, extlangs=extlangs,
            script=script, region=region, variants=variants,
            extensions=extensions, private=private
        )
        cls._INSTANCES[values] = instance
        return instance

    @staticmethod
    def get(tag: str, normalize=True) -> 'Language':
        """
        Create a Language object from a language tag string.

        If normalize=True, non-standard or overlong tags will be replaced as
        they're interpreted. This is recommended.

        Here are several examples of language codes, which are also test cases.
        Most language codes are straightforward, but these examples will get
        pretty obscure toward the end.

        >>> Language.get('en-US')
        Language.make(language='en', region='US')

        >>> Language.get('zh-Hant')
        Language.make(language='zh', script='Hant')

        >>> Language.get('und')
        Language.make()

        The non-code 'root' is sometimes used to represent the lack of any
        language information, similar to 'und'.

        >>> Language.get('root')
        Language.make()

        By default, getting a Language object will automatically convert
        deprecated tags:

        >>> Language.get('iw')
        Language.make(language='he')

        >>> Language.get('in')
        Language.make(language='id')

        One type of deprecated tag that should be replaced is for sign
        languages, which used to all be coded as regional variants of a
        fictitious global sign language called 'sgn'. Of course, there is no
        global sign language, so sign languages now have their own language
        codes.

        >>> Language.get('sgn-US')
        Language.make(language='ase')

        >>> Language.get('sgn-US', normalize=False)
        Language.make(language='sgn', region='US')

        'en-gb-oed' is a tag that's grandfathered into the standard because it
        has been used to mean "spell-check this with Oxford English Dictionary
        spelling", but that tag has the wrong shape. We interpret this as the
        new standardized tag 'en-gb-oxendict', unless asked not to normalize.

        >>> Language.get('en-gb-oed')
        Language.make(language='en', region='GB', variants=['oxendict'])

        >>> Language.get('en-gb-oed', normalize=False)
        Language.make(language='en-gb-oed')

        'zh-min-nan' is another oddly-formed tag, used to represent the
        Southern Min language, which includes Taiwanese as a regional form. It
        now has its own language code.

        >>> Language.get('zh-min-nan')
        Language.make(language='nan')

        There's not much we can do with the vague tag 'zh-min':

        >>> Language.get('zh-min')
        Language.make(language='zh-min')

        Occasionally Wiktionary will use 'extlang' tags in strange ways, such
        as using the tag 'und-ibe' for some unspecified Iberian language.

        >>> Language.get('und-ibe')
        Language.make(extlangs=['ibe'])

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

        >>> Language.get('sh-QU')
        Language.make(language='sr', script='Latn', region='EU')
        """
        if (tag, normalize) in Language._PARSE_CACHE:
            return Language._PARSE_CACHE[tag, normalize]

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
                        Language.get(norm, normalize).to_dict()
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
                        Language.get(replacement, normalize).to_dict()
                    )
                else:
                    data['language'] = value
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

        result = Language.make(**data)
        Language._PARSE_CACHE[tag, normalize] = result
        return result

    def to_tag(self) -> str:
        """
        Convert a Language back to a standard language tag, as a string.
        This is also the str() representation of a Language object.

        >>> Language.make(language='en', region='GB').to_tag()
        'en-GB'

        >>> Language.make(language='yue', script='Hant', region='HK').to_tag()
        'yue-Hant-HK'

        >>> Language.make(script='Arab').to_tag()
        'und-Arab'

        >>> str(Language.make(region='IN'))
        'und-IN'
        """
        if self._str_tag is not None:
            return self._str_tag
        subtags = ['und']
        if self.language:
            subtags[0] = self.language
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
        self._str_tag = '-'.join(subtags)
        return self._str_tag

    def simplify_script(self) -> 'Language':
        """
        Remove the script from some parsed language data, if the script is
        redundant with the language.

        >>> Language.make(language='en', script='Latn').simplify_script()
        Language.make(language='en')

        >>> Language.make(language='yi', script='Latn').simplify_script()
        Language.make(language='yi', script='Latn')

        >>> Language.make(language='yi', script='Hebr').simplify_script()
        Language.make(language='yi')
        """
        if self._simplified is not None:
            return self._simplified

        if self.language and self.script:
            if DB.default_scripts.get(self.language) == self.script:
                result = self.update_dict({'script': None})
                self._simplified = result
                return self._simplified

        self._simplified = self
        return self._simplified

    def assume_script(self) -> 'Language':
        """
        Fill in the script if it's missing, and if it can be assumed from the
        language subtag. This is the opposite of `simplify_script`.

        >>> Language.make(language='en').assume_script()
        Language.make(language='en', script='Latn')

        >>> Language.make(language='yi').assume_script()
        Language.make(language='yi', script='Hebr')

        >>> Language.make(language='yi', script='Latn').assume_script()
        Language.make(language='yi', script='Latn')

        This fills in nothing when the script cannot be assumed -- such as when
        the language has multiple scripts, or it has no standard orthography:

        >>> Language.make(language='sr').assume_script()
        Language.make(language='sr')

        >>> Language.make(language='eee').assume_script()
        Language.make(language='eee')

        It also dosn't fill anything in when the language is unspecified.

        >>> Language.make(region='US').assume_script()
        Language.make(region='US')
        """
        if self._assumed is not None:
            return self._assumed
        if self.language and not self.script:
            try:
                self._assumed = self.update_dict({'script': DB.default_scripts[self.language]})
            except KeyError:
                self._assumed = self
        else:
            self._assumed = self
        return self._assumed

    def prefer_macrolanguage(self) -> 'Language':
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

        So, applying `prefer_macrolanguage` to a Language object will
        return a new object, replacing the language with the macrolanguage if
        it is the dominant language within that macrolanguage. It will leave
        non-dominant languages that have macrolanguages alone.

        >>> Language.get('arb').prefer_macrolanguage()
        Language.make(language='ar')

        >>> Language.get('cmn-Hant').prefer_macrolanguage()
        Language.make(language='zh', script='Hant')

        >>> Language.get('yue-Hant').prefer_macrolanguage()
        Language.make(language='yue', script='Hant')
        """
        if self._macrolanguage is not None:
            return self._macrolanguage
        language = self.language or 'und'
        if language in DB.normalized_macrolanguages:
            self._macrolanguage = self.update_dict({
                'language': DB.normalized_macrolanguages[language]
            })
        else:
            self._macrolanguage = self
        return self._macrolanguage

    def broaden(self) -> 'List[Language]':
        """
        Iterate through increasingly general versions of this parsed language tag.

        This isn't actually that useful for matching two arbitrary language tags
        against each other, but it is useful for matching them against a known
        standardized form, such as in the CLDR data.

        The list of broader versions to try appears in UTR 35, section 4.3,
        "Likely Subtags".

        >>> for langdata in Language.get('nn-Latn-NO-x-thingy').broaden():
        ...     print(langdata)
        nn-Latn-NO-x-thingy
        nn-Latn-NO
        nn-NO
        nn-Latn
        nn
        und-Latn
        und
        """
        if self._broader is not None:
            return self._broader
        self._broader = [self]
        seen = set(self.to_tag())
        for keyset in self.BROADER_KEYSETS:
            filtered = self._filter_attributes(keyset)
            tag = filtered.to_tag()
            if tag not in seen:
                self._broader.append(filtered)
                seen.add(tag)
        return self._broader

    def matchable_tags(self) -> 'List[Language]':
        if self._matchable_tags is not None:
            return self._matchable_tags
        self._matchable_tags = []
        for keyset in self.MATCHABLE_KEYSETS:
            filtered_tag = self._filter_attributes(keyset).to_tag()
            self._matchable_tags.append(filtered_tag)
        return self._matchable_tags

    def maximize(self) -> 'Language':
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

        >>> str(Language.get('zh-Hant').maximize())
        'zh-Hant-TW'
        >>> str(Language.get('zh-TW').maximize())
        'zh-Hant-TW'
        >>> str(Language.get('ja').maximize())
        'ja-Jpan-JP'
        >>> str(Language.get('pt').maximize())
        'pt-Latn-BR'
        >>> str(Language.get('und-Arab').maximize())
        'ar-Arab-EG'
        >>> str(Language.get('und-CH').maximize())
        'de-Latn-CH'
        >>> str(Language.make().maximize())    # 'MURICA.
        'en-Latn-US'
        >>> str(Language.get('und-ibe').maximize())
        'en-ibe-Latn-US'
        """
        if self._filled is not None:
            return self._filled

        for broader in self.broaden():
            tag = broader.to_tag()
            if tag in DB.likely_subtags:
                result = Language.get(DB.likely_subtags[tag], normalize=False)
                result = result.update(self)
                self._filled = result
                return result

        raise RuntimeError(
            "Couldn't fill in likely values. This represents a problem with "
            "DB.likely_subtags."
        )

    # Support an old, wordier name for the method
    fill_likely_values = maximize

    def match_score(self, supported: 'Language') -> int:
        """
        Suppose that `self` is the language that the user desires, and
        `supported` is a language that is actually supported. This method
        returns a number from 0 to 100 indicating how similar the supported
        language is (higher numbers are better). This is not a symmetric
        relation.

        The algorithm here is described (badly) in a Unicode technical report
        at http://unicode.org/reports/tr35/#LanguageMatching. If you find these
        results bothersome, take it up with Unicode, unless it's particular
        tweaks we implemented such as macrolanguage matching.

        See :func:`tag_match_score` for a function that works on strings,
        instead of requiring you to instantiate Language objects first.
        Further documentation and examples appear with that function.
        """
        if supported == self:
            return 100

        desired_complete = self.prefer_macrolanguage().maximize()
        supported_complete = supported.prefer_macrolanguage().maximize()

        desired_triple = (desired_complete.language, desired_complete.script, desired_complete.region)
        supported_triple = (supported_complete.language, supported_complete.script, supported_complete.region)

        return 100 - raw_distance(desired_triple, supported_triple)

    # These methods help to show what the language tag means in natural
    # language. They actually apply the language-matching algorithm to find
    # the right language to name things in.

    def _get_name(self, attribute: str, language, min_score: int):
        assert attribute in self.ATTRIBUTES
        if isinstance(language, Language):
            language = language.to_tag()

        names = DB.names_for(attribute, getattr(self, attribute))
        names['und'] = getattr(self, attribute)
        return self._best_name(names, language, min_score)

    def _best_name(self, names: dict, language: str, min_score: int):
        possible_languages = sorted(names.keys())
        target_language, score = best_match(language, possible_languages, min_score)
        return names[target_language]

    def language_name(self, language=DEFAULT_LANGUAGE, min_score: int=75) -> str:
        """
        Give the name of the language (not the entire tag, just the language part)
        in a natural language. The target language can be given as a string or
        another Language object.

        By default, things are named in English:

        >>> Language.get('fr').language_name()
        'French'
        >>> Language.get('el').language_name()
        'Greek'

        But you can ask for language names in numerous other languages:

        >>> Language.get('fr').language_name('fr')
        'français'
        >>> Language.get('el').language_name('fr')
        'grec'

        Why does everyone get Slovak and Slovenian confused? Let's ask them.

        >>> Language.get('sl').language_name('sl')
        'slovenščina'
        >>> Language.get('sk').language_name('sk')
        'slovenčina'
        >>> Language.get('sl').language_name('sk')
        'slovinčina'
        >>> Language.get('sk').language_name('sl')
        'slovaščina'
        """
        return self._get_name('language', language, min_score)

    def autonym(self, min_score: int=75) -> str:
        """
        Give the name of this language *in* this language.

        >>> Language.get('fr').autonym()
        'français'
        >>> Language.get('es').autonym()
        'español'
        >>> Language.get('ja').autonym()
        '日本語'

        This doesn't give the name of the region or script, but in some cases
        the language can name itself in multiple scripts:

        >>> Language.get('sr-Latn').autonym()
        'srpski'
        >>> Language.get('sr-Cyrl').autonym()
        'српски'
        >>> Language.get('pa').autonym()
        'ਪੰਜਾਬੀ'
        >>> Language.get('pa-Arab').autonym()
        'پنجابی'

        This only works for language codes that CLDR has locale data for. You
        can't ask for the autonym of 'ja-Latn' and get 'nihongo'.
        """
        return self.language_name(language=self, min_score=min_score)

    def script_name(self, language=DEFAULT_LANGUAGE, min_score: int=75) -> str:
        """
        Describe the script part of the language tag in a natural language.
        """
        return self._get_name('script', language, min_score)

    def region_name(self, language=DEFAULT_LANGUAGE, min_score: int=75) -> str:
        """
        Describe the region part of the language tag in a natural language.
        """
        return self._get_name('region', language, min_score)

    def variant_names(self, language=DEFAULT_LANGUAGE, min_score: int=75) -> list:
        """
        Describe each of the variant parts of the language tag in a natural
        language.
        """
        names = []
        for variant in self.variants:
            var_names = DB.names_for('variant', variant)
            names.append(self._best_name(var_names, language, min_score))
        return names

    def describe(self, language=DEFAULT_LANGUAGE, min_score: int=75) -> dict:
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
        >>> shaw = Language.make(script='Shaw').maximize()
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

        >>> pprint(Language.get('lol').maximize().describe())
        {'language': 'Mongo', 'region': 'Congo - Kinshasa', 'script': 'Latin'}

        Sometimes the normalized and un-normalized versions of a language code
        have different descriptions:

        >>> Language.get('mo')
        Language.make(language='ro', region='MD')

        >>> pprint(Language.get('mo').describe())
        {'language': 'Romanian', 'region': 'Moldova'}

        >>> pprint(Language.get('mo', normalize=False).describe())
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
    def find_name(tagtype: str, name: str, language: {str, 'Language', None}=None):
        """
        Find the subtag of a particular `tagtype` that has the given `name`.

        This is not a particularly powerful full-text search. It ignores case, but
        otherwise it expects the name to appear exactly the way it does in one of
        the databases that langcodes uses. If the exact name isn't found, you get a
        LookupError.

        This method used to require a `language` parameter, when it was possible to
        get different results based on what language the name you were looking up
        was in. Names are now an unambiguous many-to-one mapping, and the `language`
        parameter is ignored and causes a PendingDeprecationWarning.

        >>> Language.find_name('language', 'francés')
        Language.make(language='fr')

        >>> Language.find_name('region', 'United Kingdom')
        Language.make(region='GB')

        >>> Language.find_name('script', 'Arabic')
        Language.make(script='Arab')

        >>> Language.find_name('language', 'norsk bokmål')
        Language.make(language='nb')

        >>> Language.find_name('language', 'norsk bokmal')
        Traceback (most recent call last):
            ...
        LookupError: Can't find any language named 'norsk bokmal'

        Some langauge names resolve to more than a language. For example,
        the name 'Brazilian Portuguese' resolves to a language and a region,
        and 'Simplified Chinese' resolves to a language and a script. In these
        cases, a Language object with multiple subtags will be returned.

        >>> Language.find_name('language', 'Brazilian Portuguese', 'en')
        Language.make(language='pt', region='BR')
        >>> Language.find_name('language', 'Simplified Chinese', 'en')
        Language.make(language='zh', script='Hans')
        """
        if language is not None:
            warnings.warn(
                "find_name no longer requires or uses the `language` parameter.",
                PendingDeprecationWarning
            )

        code = DB.lookup_name(tagtype, name)
        if '-' in code:
            return Language.get(code)
        else:
            data = {tagtype: code}
            return Language.make(**data)

    @staticmethod
    def find(name: str):
        """
        A concise version of `find_name`, used to get a language tag by its
        name in any natural language.

        >>> Language.find('Türkçe')
        Language.make(language='tr')
        >>> Language.find('brazilian portuguese')
        Language.make(language='pt', region='BR')
        >>> Language.find('simplified chinese')
        Language.make(language='zh', script='Hans')
        """
        return Language.find_name('language', name)

    def to_dict(self):
        """
        Get a dictionary of the attributes of this Language object, which
        can be useful for constructing a similar object.
        """
        if self._dict is not None:
            return self._dict

        result = {}
        for key in self.ATTRIBUTES:
            value = getattr(self, key)
            if value:
                result[key] = value
        self._dict = result
        return result

    def update(self, other: 'Language') -> 'Language':
        """
        Update this Language with the fields of another Language.
        """
        return Language.make(
            language=other.language or self.language,
            extlangs=other.extlangs or self.extlangs,
            script=other.script or self.script,
            region=other.region or self.region,
            variants=other.variants or self.variants,
            extensions=other.extensions or self.extensions,
            private=other.private or self.private
        )

    def update_dict(self, newdata: dict) -> 'Language':
        """
        Update the attributes of this Language from a dictionary.
        """
        return Language.make(
            language=newdata.get('language', self.language),
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
        return Language.make(**filtered)

    def _searchable_form(self) -> 'Language':
        """
        Convert a parsed language tag so that the information it contains is in
        the best form for looking up information in the CLDR.
        """
        if self._searchable is not None:
            return self._searchable

        self._searchable = self._filter_attributes(
            {'language', 'script', 'region'}
        ).simplify_script().prefer_macrolanguage()
        return self._searchable

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, Language):
            return False
        return self._str_tag == other._str_tag

    def __hash__(self):
        return hash(id(self))

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
                items.append('{0}={1!r}'.format(attr, getattr(self, attr)))
        return "Language.make({})".format(', '.join(items))

    def __str__(self):
        return self.to_tag()


# Make the get(), find(), and find_name() functions available at the top level
get = Language.get
find = Language.find
find_name = Language.find_name

# Make the Language object available under the old name LanguageData
LanguageData = Language


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
    langdata = Language.get(tag, normalize=True)
    if macro:
        langdata = langdata.prefer_macrolanguage()

    return langdata.simplify_script().to_tag()


def tag_match_score(desired: str, supported: str) -> int:
    """
    Return a number from 0 to 100 indicating the strength of match between the
    language the user desires, D, and a supported language, S. Higher numbers
    are better. A reasonable cutoff for not messing with your users is to
    only accept scores of 75 or more.

    A score of 100 means the languages are the same, possibly after normalizing
    and filling in likely values.

    >>> tag_match_score('en', 'en')
    100
    >>> tag_match_score('en', 'en-US')
    100
    >>> tag_match_score('zh-Hant', 'zh-TW')
    100
    >>> tag_match_score('ru-Cyrl', 'ru')
    100
    >>> # Serbo-Croatian is a politically contentious idea, but in practice
    >>> # it's considered equivalent to Serbian in Latin characters.
    >>> tag_match_score('sh', 'sr-Latn')
    100

    A score of 92 to 97 indicates a regional difference.

    >>> tag_match_score('zh-HK', 'zh-MO')   # Chinese is similar in Hong Kong and Macao
    97
    >>> tag_match_score('en-AU', 'en-GB')   # Australian English is similar to British English
    96
    >>> tag_match_score('en-IN', 'en-GB')   # Indian English is also similar to British English
    96
    >>> tag_match_score('es-PR', 'es-419')  # Peruvian Spanish is Latin American Spanish
    96
    >>> tag_match_score('en-US', 'en-GB')   # American and British English are somewhat different
    94
    >>> tag_match_score('es-MX', 'es-ES')   # Mexican Spanish is different from Spanish Spanish
    92
    >>> # Serbian has two scripts, and people might prefer one but understand both
    >>> tag_match_score('sr-Latn', 'sr-Cyrl')
    95
    >>> # European Portuguese is different from the most common form (Brazilian Portuguese)
    >>> tag_match_score('pt', 'pt-PT')
    92

    A score of 86 to 90 indicates that people who use the desired language
    are demographically likely to understand the supported language, even if
    the languages themselves are unrelated. There are many languages that have
    a one-way connection of this kind to English or French.

    >>> tag_match_score('ta', 'en')  # Tamil to English
    86
    >>> tag_match_score('mg', 'fr')  # Malagasy to French
    86

    Sometimes it's more straightforward than that: people who use the desired
    language are demographically likely to understand the supported language
    because it's demographically relevant and highly related.

    >>> tag_match_score('af', 'nl')  # Afrikaans to Dutch
    86
    >>> tag_match_score('ms', 'id')  # Malay to Indonesian
    86
    >>> tag_match_score('nn', 'nb')  # Nynorsk to Norwegian Bokmål
    90
    >>> tag_match_score('nb', 'da')  # Norwegian Bokmål to Danish
    88

    A score of 80 to 85 indicates a particularly contentious difference in
    script, where people who understand one script can learn the other but
    probably won't be happy with it. This specifically applies to Chinese.

    >>> tag_match_score('zh-Hans', 'zh-Hant')
    85
    >>> tag_match_score('zh-CN', 'zh-HK')
    85
    >>> tag_match_score('zh-CN', 'zh-TW')
    85
    >>> tag_match_score('zh-Hant', 'zh-Hans')
    81
    >>> tag_match_score('zh-TW', 'zh-CN')
    81

    When the supported script is a different one than desired, this is usually
    a major difference with score of 60 or less.

    >>> tag_match_score('ja', 'ja-Latn-US-hepburn')
    56

    >>> # You can read the Shavian script, right?
    >>> tag_match_score('en', 'en-Shaw')
    56

    When there is no indication the supported language will be understood, the
    score will be 20 or less, to a minimum of 0.

    >>> tag_match_score('es', 'fr')   # Spanish and French are different.
    16
    >>> tag_match_score('en', 'ta')   # English speakers generally do not know Tamil.
    0

    CLDR doesn't take into account which languages are considered part of a
    common 'macrolanguage'. We have this data, so we can use it in matching.
    If two languages have no other rule that would allow them to match, but
    share a macrolanguage, they'll get a match score of 20 less than what
    they would get if the language matched.

    >>> tag_match_score('arz', 'ar')   # Egyptian Arabic to Standard Arabic
    80
    >>> tag_match_score('arz', 'ary')  # Egyptian Arabic to Moroccan Arabic
    76

    Here's an example that has script, region, and language differences, but
    a macrolanguage in common.

    Written Chinese is usually presumed to be Mandarin Chinese, but colloquial
    Cantonese can be written as well. When it is, it probably has region,
    script, and language differences from the usual mainland Chinese. But it is
    still part of the 'Chinese' macrolanguage, so there is more similarity
    than, say, comparing Mandarin to Hindi.

    >>> tag_match_score('yue', 'zh')
    36

    Comparing Swiss German ('gsw') to standardized German ('de') shows how
    these scores can be asymmetrical. Swiss German speakers will understand
    German, so the score in that direction is 92. Most German speakers find
    Swiss German unintelligible, and CLDR in fact assigns this a score of 16.

    This seems a little bit extreme, but the asymmetry is certainly there. And
    if your text is tagged as 'gsw', it must be that way for a reason.

    >>> tag_match_score('gsw', 'de')
    92
    >>> tag_match_score('de', 'gsw')
    16
    """
    desired_ld = Language.get(desired)
    supported_ld = Language.get(supported)
    return desired_ld.match_score(supported_ld)


def best_match(desired_language: str, supported_languages: list,
               min_score: int=75) -> (str, int):
    """
    You have software that supports any of the `supported_languages`. You want
    to use `desired_language`. This function lets you choose the right language,
    even if there isn't an exact match.

    Returns:

    - The best-matching language code, which will be one of the
      `supported_languages` or 'und'
    - The score of the match, from 0 to 100

    `min_score` sets the minimum match score. If all languages match with a lower
    score than that, the result will be 'und' with a score of 0.

    When there is a tie for the best matching language, the first one in the
    tie will be used.

    Setting `min_score` lower will enable more things to match, at the cost
    of possibly mis-handling data or upsetting users. Read the documentation
    for :func:`tag_match_score` to understand what the numbers mean.

    >>> best_match('fr', ['de', 'en', 'fr'])
    ('fr', 100)
    >>> best_match('sh', ['hr', 'bs', 'sr-Latn', 'sr-Cyrl'])
    ('sr-Latn', 100)
    >>> best_match('zh-CN', ['zh-Hant', 'zh-Hans', 'gan', 'nan'])
    ('zh-Hans', 100)
    >>> best_match('zh-CN', ['cmn-Hant', 'cmn-Hans', 'gan', 'nan'])
    ('cmn-Hans', 100)
    >>> best_match('pt', ['pt-BR', 'pt-PT'])
    ('pt-BR', 100)
    >>> best_match('en-AU', ['en-GB', 'en-US'])
    ('en-GB', 96)
    >>> best_match('es-MX', ['es-ES', 'es-419', 'en-US'])
    ('es-419', 96)
    >>> best_match('es-MX', ['es-PU', 'es-AR', 'es-PY'])
    ('es-PU', 95)
    >>> best_match('es-MX', ['es-AR', 'es-PU', 'es-PY'])
    ('es-AR', 95)
    >>> best_match('zsm', ['id', 'mhp'])
    ('id', 86)
    >>> best_match('eu', ['el', 'en', 'es'])
    ('es', 90)
    >>> best_match('eu', ['el', 'en', 'es'], min_score=92)
    ('und', 0)

    TODO:

        - let parentLocales divert the way languages match
    """
    # Quickly return if the desired language is directly supported
    if desired_language in supported_languages:
        return desired_language, 100

    # Reduce the desired language to a standard form that could also match
    desired_language = standardize_tag(desired_language)
    if desired_language in supported_languages:
        return desired_language, 100

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
