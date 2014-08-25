from .tag_parser import parse
from .db import LanguageDB, LIKELY_SUBTAGS, LANGUAGE_MATCHING, PARENT_LOCALES
from .util import data_filename
import logging

DB = LanguageDB(data_filename('subtags.db'))

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
    meaning = tag_to_meaning(tag, normalize=True)
    if macro:
        meaning = prefer_macrolanguage(meaning)
    return meaning_to_tag(simplify_script(meaning))


def tag_to_meaning(tag: str, normalize=True) -> dict:
    """
    Convert a language tag into a dictionary that specifies what its parts
    mean. The function names and documentation refer to this as a 'meaning'.

    If normalize=True, non-standard or overlong tags will be replaced as
    they're interpreted. This is recommended.

    >>> from pprint import pprint
    >>> pprint(tag_to_meaning('en-US'))
    {'language': 'en', 'region': 'US'}

    >>> pprint(tag_to_meaning('sh-QU'))        # transform deprecated tags
    {'language': 'sr', 'macrolanguage': 'sh', 'region': 'EU', 'script': 'Latn'}

    >>> pprint(tag_to_meaning('sgn-US'))
    {'language': 'ase'}

    >>> pprint(tag_to_meaning('sgn-US', normalize=False))
    {'language': 'sgn', 'region': 'US'}

    >>> pprint(tag_to_meaning('zh-cmn-Hant'))  # promote extlangs to languages
    {'language': 'cmn', 'macrolanguage': 'zh', 'script': 'Hant'}

    >>> pprint(tag_to_meaning('zh-cmn-Hant', normalize=False))
    {'extlang': {'cmn'}, 'language': 'zh', 'script': 'Hant'}
    """
    meaning = {}
    # if the complete tag appears as something to normalize, do the
    # normalization right away. Smash case when checking, because the
    # case normalization that comes from parse() hasn't been applied yet.
    if normalize and tag.lower() in NORMALIZED_LANGUAGES:
        tag = NORMALIZED_LANGUAGES[tag.lower()]

    components = parse(tag)

    for typ, value in components:
        if typ == 'extlang' and normalize and meaning['language']:
            # smash extlangs when possible
            minitag = '%s-%s' % (meaning['language'], value)
            if minitag in NORMALIZED_LANGUAGES:
                meaning.update(tag_to_meaning(NORMALIZED_LANGUAGES[minitag], normalize))
            else:
                meaning.setdefault(typ, set()).add(value)
        elif typ in {'extlang', 'variant', 'extension'}:
            meaning.setdefault(typ, set()).add(value)
        elif typ == 'language':
            if value == 'und':
                pass
            elif normalize and value in NORMALIZED_LANGUAGES:
                replacement = NORMALIZED_LANGUAGES[value]
                # parse the replacement if necessary -- this helps with
                # Serbian and Moldovan
                meaning.update(tag_to_meaning(replacement, normalize))
            else:
                meaning[typ] = value
                if value in MACROLANGUAGES:
                    meaning['macrolanguage'] = MACROLANGUAGES[value]
        elif typ == 'region':
            if normalize and value in NORMALIZED_REGIONS:
                meaning[typ] = NORMALIZED_REGIONS[value]
            else:
                meaning[typ] = value
        else:
            meaning[typ] = value
    return meaning


def prefer_macrolanguage(meaning: dict) -> dict:
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

    So, applying `prefer_macrolanguage` to a meaning dictionary will replace
    the language with the macrolanguage if it is the dominant language within
    that macrolanguage. It will leave non-dominant languages that have
    macrolanguages alone.

    >>> from pprint import pprint
    >>> pprint(prefer_macrolanguage(tag_to_meaning('arb')))
    {'language': 'ar'}

    >>> pprint(prefer_macrolanguage(tag_to_meaning('cmn-Hant')))
    {'language': 'zh', 'script': 'Hant'}

    >>> pprint(prefer_macrolanguage(tag_to_meaning('yue-Hant')))
    {'language': 'yue', 'macrolanguage': 'zh', 'script': 'Hant'}
    """
    language = meaning.get('language', 'und')
    if language in NORMALIZED_MACROLANGUAGES:
        copied = dict(meaning)
        copied['language'] = NORMALIZED_MACROLANGUAGES[language]
        if 'macrolanguage' in copied:
            del copied['macrolanguage']
        return copied
    else:
        return meaning


def meaning_to_tag(meaning: dict) -> str:
    """
    Convert a meaning dictionary back to a standard language tag, as a
    string.

    >>> meaning_to_tag({'language': 'en', 'region': 'GB'})
    'en-GB'

    >>> meaning_to_tag({'macrolanguage': 'zh', 'language': 'yue',
    ...                 'script': 'Hant', 'region': 'HK'})
    'yue-Hant-HK'

    >>> meaning_to_tag({'script': 'Arab'})
    'und-Arab'

    >>> meaning_to_tag({'region': 'IN'})
    'und-IN'
    """
    subtags = ['und']
    if 'language' in meaning:
        subtags[0] = meaning['language']
    elif 'macrolanguage' in meaning:
        subtags[0] = meaning['macrolanguage']
    if 'script' in meaning:
        subtags.append(meaning['script'])
    if 'region' in meaning:
        subtags.append(meaning['region'])
    if 'variant' in meaning:
        variants = sorted(meaning['variant'])
        for variant in variants:
            subtags.append(variant)
    if 'extension' in meaning:
        extensions = sorted(meaning['extension'])
        for ext in extensions:
            subtags.append(ext)
    if 'private' in meaning:
        subtags.append(meaning['private'])
    return '-'.join(subtags)


def simplify_script(meaning: dict) -> dict:
    """
    Remove the script from a language tag's interpreted meaning, if the
    script is redundant with the language.

    >>> meaning_to_tag(simplify_script({'language': 'en', 'script': 'Latn'}))
    'en'
    
    >>> meaning_to_tag(simplify_script({'language': 'yi', 'script': 'Latn'}))
    'yi-Latn'

    >>> meaning_to_tag(simplify_script({'language': 'yi', 'script': 'Hebr'}))
    'yi'
    """
    if 'language' in meaning and 'script' in meaning:
        if DEFAULT_SCRIPTS.get(meaning['language']) == meaning['script']:
            copied = dict(meaning)
            del copied['script']
            return copied

    return meaning


def assume_script(meaning: dict) -> dict:
    """
    Fill in the script if it's missing, and if it can be assumed from the
    language subtag. This is the opposite of `simplify_script`.
    
    >>> meaning_to_tag(assume_script({'language': 'en'}))
    'en-Latn'
    >>> meaning_to_tag(assume_script({'language': 'yi'}))
    'yi-Hebr'
    >>> meaning_to_tag(assume_script({'language': 'yi', 'script': 'Latn'}))
    'yi-Latn'

    This fills in nothing when the script cannot be assumed -- such as when
    the language has multiple scripts, or it has no standard orthography:

    >>> meaning_to_tag(assume_script({'language': 'sr'}))
    'sr'
    >>> meaning_to_tag(assume_script({'language': 'eee'}))
    'eee'

    It also dosn't fill anything in when the language is unspecified.

    >>> meaning_to_tag(assume_script({'region': 'US'}))
    'und-US'
    """
    if 'language' in meaning and 'script' not in meaning:
        lang = meaning['language']
        copied = dict(meaning)
        try:
            copied['script'] = DEFAULT_SCRIPTS[lang]
        except KeyError:
            pass
        return copied
    else:
        return meaning


def meaning_superset(meaning1: dict, meaning2: dict) -> bool:
    """
    Determine if the dictionary of information `meaning1` encompasses
    the information in `meaning2` -- that is, if `meaning2` is equal to
    or more specific than `meaning1`.

    This simply looks at the values in the dictionary; it does not determine,
    for example, that 'ar' encompasses 'arb'.

    >>> meaning_superset({}, {})
    True
    >>> meaning_superset({}, {'language': 'en'})
    True
    >>> meaning_superset({'language': 'en'}, {})
    False
    >>> meaning_superset({'language': 'zh', 'region': 'HK'},
    ...                  {'language': 'zh', 'script': 'Hant', 'region': 'HK'})
    True
    >>> meaning_superset({'language': 'zh', 'script': 'Hant', 'region': 'HK'},
    ...                  {'language': 'zh', 'region': 'HK'})
    False
    >>> meaning_superset({'language': 'zh', 'region': 'CN'},
    ...                  {'language': 'zh', 'script': 'Hant', 'region': 'HK'})
    False
    >>> meaning_superset({'language': 'ja', 'script': 'Latn', 'variant': {'hepburn'}},
    ...                  {'language': 'ja', 'script': 'Latn', 'variant': {'hepburn', 'heploc'}})
    True
    >>> meaning_superset({'language': 'ja', 'script': 'Latn', 'variant': {'hepburn'}},
    ...                  {'language': 'ja', 'script': 'Latn', 'variant': {'heploc'}})
    False
    """
    for key in meaning1:
        if key not in meaning2:
            return False
        else:
            mine = meaning1[key]
            yours = meaning2[key]
            if isinstance(mine, set):
                if not mine.issubset(yours):
                    return False
            else:
                if mine != yours:
                    return False
    return True


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


def broader_meanings(meaning: dict):
    """
    Iterate through increasingly general versions of a language tag in
    "meaning" form.

    This isn't actually that useful for matching two arbitrary language tags
    against each other, but it is useful for matching them against a known
    standardized form, such as in the CLDR data.

    >>> for meaning in broader_meanings(tag_to_meaning('nn-Latn-NO-x-thing')):
    ...     print(meaning_to_tag(meaning))
    nn-Latn-NO-x-thing
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
    yield meaning
    for keyset in BROADER_KEYSETS:
        filtered = _filter_keys(meaning, keyset)
        if filtered != meaning:
            yield filtered


def _filter_keys(d: dict, keys: set) -> dict:
    """
    Select a subset of keys from a dictionary.
    """
    return {key: d[key] for key in keys if key in d}


def fill_likely_values(meaning: dict) -> dict:
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

    >>> from pprint import pprint
    >>> pprint(fill_likely_values({'language': 'zh', 'script': 'Hant'}))
    {'language': 'zh', 'region': 'TW', 'script': 'Hant'}
    >>> pprint(fill_likely_values({'language': 'zh', 'region': 'TW'}))
    {'language': 'zh', 'region': 'TW', 'script': 'Hant'}
    >>> pprint(fill_likely_values({'language': 'ja'}))
    {'language': 'ja', 'region': 'JP', 'script': 'Jpan'}
    >>> pprint(fill_likely_values({'language': 'pt'}))
    {'language': 'pt', 'region': 'BR', 'script': 'Latn'}
    >>> pprint(fill_likely_values({'script': 'Arab'}))
    {'language': 'ar', 'region': 'EG', 'script': 'Arab'}
    >>> pprint(fill_likely_values({'region': 'CH'}))
    {'language': 'de', 'region': 'CH', 'script': 'Latn'}
    >>> pprint(fill_likely_values({}))   # 'MURICA.
    {'language': 'en', 'region': 'US', 'script': 'Latn'}
    """
    for check_meaning in broader_meanings(meaning):
        tag = meaning_to_tag(check_meaning)
        if tag in LIKELY_SUBTAGS:
            result = tag_to_meaning(LIKELY_SUBTAGS[tag])
            result.update(meaning)
            return result
    raise RuntimeError(
        "Couldn't fill in likely values. This represents a problem with "
        "langcodes.db.LIKELY_SUBTAGS."
    )


def _searchable_form(meaning: dict) -> dict:
    """
    Convert a language tag meaning so that the information it contains is in
    the best form for looking up information in the CLDR.
    """
    four_keys = _filter_keys(
        meaning,
        {'macrolanguage', 'language', 'script', 'region'}
    )
    return prefer_macrolanguage(simplify_script(four_keys))


def language_match_value(desired: dict, supported: dict) -> int:
    """
    Return a number from 0 to 100 indicating the strength of match between the
    language the user desires, D, and a supported language, S. The scale comes
    from CLDR data, but we've added some scale steps to deal with languages
    within macrolanguages.

    This function takes its inputs as dictionaries. See `tag_match_value` for
    the equivalent function that works on language tags as strings, including
    examples.
    """
    if desired == supported:
        return 100

    desired_complete = fill_likely_values(desired)
    supported_complete = fill_likely_values(supported)
    desired_reduced = _searchable_form(desired_complete)
    supported_reduced = _searchable_form(supported_complete)

    # if the languages match after we normalize them, that's very good
    if desired_reduced == supported_reduced:
        return 99

    # CLDR doesn't tell us how to combine the data in 'parentLocales' with
    # that in 'languageMatching', so here's a heuristic that seems to fit.
    desired_tag = meaning_to_tag(desired_reduced)
    supported_tag = meaning_to_tag(supported_reduced)
    if PARENT_LOCALES.get(desired_tag) == supported_tag:
        return 98
    if PARENT_LOCALES.get(supported_tag) == desired_tag:
        return 97

    if desired_complete['script'] == supported_complete['script']:
        # When the scripts match, we can check for mutually intelligible
        # languages.

        dlang, slang = desired_complete['language'], supported_complete['language']
        if (dlang, slang) in LANGUAGE_MATCHING:
            return LANGUAGE_MATCHING[(dlang, slang)]
    
    if desired_complete['language'] == supported_complete['language']:
        if desired_complete['script'] == supported_complete['script']:
            return 96
        else:
            # When the scripts don't match, check for mutually intelligible scripts.
            dlang_script = meaning_to_tag(_filter_keys(desired_complete, {'language', 'script'}))
            slang_script = meaning_to_tag(_filter_keys(supported_complete, {'language', 'script'}))
            if (dlang_script, slang_script) in LANGUAGE_MATCHING:
                return LANGUAGE_MATCHING[(dlang_script, slang_script)]

        # Implement these wildcard rules about Han scripts explicitly.
        if desired_complete['script'] == 'Hans' and supported_complete['script'] == 'Hant':
            return 85
        elif desired_complete['script'] == 'Hant' and supported_complete['script'] == 'Hans':
            return 75
        else:
            # A low-ish score for incompatible scripts.
            return 20

    # FIXME: match ta-IN with en-US even though the actual match is ('ta', 'en')
    # filter for {l, r, s}, {l, r}, {l, s}, and {l}
    if (desired_tag, supported_tag) in LANGUAGE_MATCHING:
        return LANGUAGE_MATCHING[(desired_tag, supported_tag)]
    
    if 'macrolanguage' in desired_complete or 'macrolanguage' in supported_complete:
        # This rule isn't in the CLDR data, because they don't trust any
        # information about sub-languages of a macrolanguage.
        #
        # If the two language codes share a macrolanguage, we take half of
        # what their match value would be if the macrolanguage were a language.

        desired_macro = dict(desired_complete)
        supported_macro = dict(supported_complete)
        if 'macrolanguage' in desired_complete:
            desired_macro['language'] = desired_complete['macrolanguage']
            del desired_macro['macrolanguage']
        if 'macrolanguage' in supported_complete:
            supported_macro['language'] = supported_complete['macrolanguage']
            del supported_macro['macrolanguage']
        if desired_macro != desired_complete or supported_macro != supported_complete:
            return language_match_value(desired_macro, supported_macro) // 2

    # There is nothing that matches.
    # CLDR would give a match value of 1 here, for reasons I suspect are
    # internal to their own software. Forget that. 0 should mean "no match".
    return 0


def tag_match_value(desired: str, supported: str) -> int:
    """
    Return a number from 0 to 100 indicating the strength of match between the
    language the user desires, D, and a supported language, S. The scale comes
    from CLDR data, but we've added some scale steps to deal with languages
    within macrolanguages.

    A match strength of 100 indicates that the languages are the same for all
    purposes.
    
    >>> tag_match_value('en', 'en')
    100
    >>> tag_match_value('no', 'nb')  # Unspecified Norwegian means Bokmål in practice.
    100

    A match strength of 99 indicates that the languages are the same after
    filling in likely values and normalizing. There may be situations in which
    the tags differ, but users are unlikely to be bothered. A machine learning
    algorithm expecting input in language S should do just fine in language D.
    
    >>> tag_match_value('en', 'en-US')
    99
    >>> tag_match_value('zh-Hant', 'zh-TW')
    99
    >>> tag_match_value('ru-Cyrl', 'ru')
    99

    A match strength of 97 or 98 means that the language tags are different,
    but are culturally similar enough that they should be interchangeable in
    most contexts. (The CLDR provides the data about related locales, but
    doesn't assign it a match strength. It uses hacky wildcard-based rules for
    this purpose instead. The end result is very similar.)

    >>> tag_match_value('en-AU', 'en-GB')   # Australian English is similar to British
    98
    >>> tag_match_value('en-IN', 'en-GB')   # Indian English is also similar to British
    98
    >>> # It might be slightly more unexpected to ask for British usage and get
    >>> # Indian usage than the other way around.
    >>> tag_match_value('en-GB', 'en-IN')
    97
    >>> tag_match_value('es-PR', 'es-419')  # Peruvian Spanish is Latin American Spanish
    98

    A match strength of 96 means that the tags indicate a regional difference.
    Users may notice some unexpected usage, and NLP algorithms that expect one
    language may occasionally trip up on the other.
    
    >>> # European Portuguese is a bit different from the Brazilian most common dialect
    >>> tag_match_value('pt', 'pt-PT')
    96
    >>> # UK and US English are also a bit different
    >>> tag_match_value('en-GB', 'en-US')
    96
    >>> # Swiss German speakers will understand standardized German
    >>> tag_match_value('gsw', 'de')
    96
    >>> # Most German speakers will think Swiss German is a foreign language
    >>> tag_match_value('de', 'gsw')
    0

    A match strength of 90 represents languages with a considerable amount of
    overlap and some amount of mutual intelligibility. People will probably be
    able to handle the difference with a bit of discomfort
    
    Algorithms may have more trouble, but you could probably train your NLP on
    _both_ languages without any problems. Below this match strength, though,
    don't expect algorithms to be compatible.

    >>> tag_match_value('no', 'da')  # Norwegian Bokmål is like Danish
    90
    >>> tag_match_value('id', 'ms')  # Indonesian is like Malay
    90
    >>> # Serbian language users will usually understand Serbian in its other script.
    >>> tag_match_value('sr-Latn', 'sr-Cyrl')
    90

    A match strength of 85 indicates a script that well-educated users of the
    desired language will understand, but they won't necessarily be happy with
    it. In particular, those who write in Simplified Chinese can often
    understand the Traditional script.
    
    >>> tag_match_value('zh-Hans', 'zh-Hant')
    85
    >>> tag_match_value('zh-CN', 'zh-HK')
    85

    A match strength of 75 indicates a script that users of the desired language
    are passingly familiar with, but would have to go out of their way to learn.
    Those who write in Traditional Chinese are less familiar with the Simplified
    script than the other way around.

    >>> tag_match_value('zh-Hant', 'zh-Hans')
    75
    >>> tag_match_value('zh-HK', 'zh-CN')
    75

    A match strength of 50 means that the languages are different sub-languages of
    a macrolanguage. Their mutual intelligibility will vary considerably based on
    the circumstances. (Checking the macrolanguage is an extension that we added.)
    >>> # Gan is considered a kind of Chinese, but it's fairly different from Mandarin.
    >>> tag_match_value('gan', 'zh')
    50

    A match strength of 35 to 49 has one of the differences described above as well
    as being different sub-languages of a macrolanguage.

    >>> # Hong Kong uses traditional Chinese, but it may contain Cantonese-specific
    >>> # expressions that are gibberish in Mandarin, hindering intelligibility.
    >>> tag_match_value('zh-Hant', 'yue-HK')
    48
    >>> # Mainland Chinese is actually a poor match for Hong Kong Cantonese.
    >>> tag_match_value('yue-HK', 'zh-CN')
    37

    A match strength of 20 indicates that the script that's supported is a
    different one than desired. This is usually a big problem, because most
    people only read their native language in one script, and in another script
    it would be gibberish to them. I think CLDR is assuming you've got a good
    reason to support the script you support.
    >>> tag_match_value('ja', 'ja-Latn-US-hepburn')
    20
    >>> tag_match_value('en', 'en-Dsrt')
    20

    A match strength of 10 is a last resort that might be better than matching
    nothing. In most cases, it indicates that numerous speakers of language D
    happen to understand language S, despite that there might be no connection
    between the languages.

    >>> tag_match_value('ta', 'en')   # Many computer-using Tamil speakers also know English.
    10
    >>> tag_match_value('af', 'nl')   # Afrikaans and Dutch at least share history.
    10
    """


    return language_match_value(tag_to_meaning(desired), tag_to_meaning(supported))


def match_language_code(desired_language: str, supported_languages: list) -> str:
    raise NotImplementedError


def natural_language_meaning(meaning: dict, language: str='en') -> dict:
    """
    Replace the codes in a 'meaning' dictionary with their names in
    a natural language, when possible.
    """
    raise NotImplementedError
