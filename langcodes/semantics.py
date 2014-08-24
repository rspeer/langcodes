from .tag_parser import parse
from .db import LanguageDB, LIKELY_SUBTAGS, LANGUAGE_MATCHING, PARENT_LOCALES
from .util import data_filename


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

    >>> pprint(prefer_macrolanguage(tag_to_meaning('zh-cmn-Hant')))
    {'language': 'zh', 'script': 'Hant'}

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
    subtags = ['und']
    if 'language' in meaning:
        subtags[0] = meaning['language']
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


def _filter_keys(d: dict, keys: set) -> dict:
    filtered = {key: d[key] for key in keys if key in d}
    if 'macrolanguage' in filtered and 'language' not in filtered:
        filtered['language'] = filtered['macrolanguage']
        del filtered['macrolanguage']
    return filtered


def broader_meanings(meaning: dict):
    # TODO: apply all macrolanguages, and possibly region inclusions
    yield meaning
    for keyset in BROADER_KEYSETS:
        filtered = _filter_keys(meaning, keyset)
        if filtered != meaning:
            yield filtered


def fill_likely_values(meaning: dict) -> dict:
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


def _check_filtered(desired, supported, keyset):
    return (_filter_keys(desired, keyset) == _filter_keys(supported, keyset))


def _searchable_form(meaning: dict) -> dict:
    four_keys = _filter_keys(
        meaning,
        {'macrolanguage', 'language', 'script', 'region'}
    )
    return prefer_macrolanguage(simplify_script(four_keys))


def language_match_value(desired: dict, supported: dict) -> int:
    if desired == supported:
        return 100
    desired_complete = fill_likely_values(desired)
    supported_complete = fill_likely_values(supported)
    desired_reduced = _searchable_form(desired_complete)
    supported_reduced = _searchable_form(supported_complete)

    # if the languages match after we normalize them, that's very good
    if desired_reduced == supported_reduced:
        return 99

    # When a language tag matches another tag's "parent locale" exactly,
    # that's a very good match.
    desired_tag = meaning_to_tag(desired_reduced)
    supported_tag = meaning_to_tag(supported_reduced)
    if PARENT_LOCALES.get(desired_tag) == supported_tag:
        return 98
    if PARENT_LOCALES.get(supported_tag) == desired_tag:
        return 97

    if (desired_tag, supported_tag) in LANGUAGE_MATCHING:
        return LANGUAGE_MATCHING[(desired_tag, supported_tag)]
    
    if desired_complete['script'] == supported_complete['script']:
        # When the scripts match, we can check for mutually intelligible
        # languages.
        dlang, slang = desired_complete['language'], supported_complete['language']
        if (dlang, slang) in LANGUAGE_MATCHING:
            return LANGUAGE_MATCHING[(dlang, slang)]
    
    if desired_complete['language'] == supported_complete['language']:
        # We also have some information about mutually intelligible scripts.
        if desired_complete['script'] == supported_complete['script']:
            return 96
        if desired_complete['script'] == 'Hans' and supported_complete['script'] == 'Hant':
            return 85
        elif desired_complete['script'] == 'Hant' and supported_complete['script'] == 'Hans':
            return 75
        else:
            # Most scripts aren't mutually intelligible. I don't know why CLDR
            # gives this a value as high as 20.
            return 20


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
        if 'macrolanguage' in supported_complete:
            supported_macro['language'] = supported_complete['macrolanguage']
        if desired_macro != desired_complete or supported_macro != supported_complete:
            return language_match_value(desired_macro, supported_macro) // 2

    # There is nothing that matches.
    # CLDR would give a match value of 1 here, for reasons I suspect are
    # internal to their own software. Forget that. 0 should mean "no match".
    return 0


def tag_match_value(desired: str, supported: str):
    return language_match_value(tag_to_meaning(desired), tag_to_meaning(supported))


def match_language_code(desired_language: str, supported_languages: list) -> str:
    raise NotImplementedError


def natural_language_meaning(meaning: dict, language: str='en') -> dict:
    """
    Replace the codes in a 'meaning' dictionary with their names in
    a natural language, when possible.
    """
    raise NotImplementedError
