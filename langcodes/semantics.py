from .tag_parser import parse
from .db import LanguageDB
from .util import data_filename
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


DB = LanguageDB(data_filename('subtags.db'))

# Non-standard codes that should be unconditionally replaced.
NORMALIZED_LANGUAGES = {orig.lower(): new.lower()
                        for (orig, new) in DB.language_replacements()}

# Codes that the Unicode Consortium would rather replace with macrolanguages.
NORMALIZED_MACROLANGUAGES = {
    orig.lower(): new
    for (orig, new) in DB.language_replacements(macro=True)
}

NORMALIZED_REGIONS = {
    orig.upper(): new.upper()
    for (orig, new) in DB.region_replacements()
}

SUPPRESSED_SCRIPTS = {
    lang: script
    for (lang, script) in DB.suppressed_scripts()
}


def standardize_tag(tag: str, macro=False) -> str:
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
    by Unicode.

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
    if macro:
        normalize = 'macro'
    else:
        normalize = True
    return meaning_to_tag(simplify_script(
        tag_to_meaning(tag, normalize=normalize)
    ))


def tag_to_meaning(tag: str, normalize=True) -> dict:
    """
    >>> from pprint import pprint

    >>> pprint(tag_to_meaning('en-US'))
    {'language': 'en', 'region': 'US'}

    >>> pprint(tag_to_meaning('sh-QU'))        # transform deprecated tags
    {'language': 'sr', 'region': 'EU', 'script': 'Latn'}

    >>> pprint(tag_to_meaning('sgn-US'))
    {'language': 'ase'}

    >>> pprint(tag_to_meaning('sgn-US', normalize=False))
    {'language': 'sgn', 'region': 'US'}

    >>> pprint(tag_to_meaning('zh-cmn-Hant'))  # promote extlangs to languages
    {'language': 'cmn', 'script': 'Hant'}

    >>> pprint(tag_to_meaning('zh-cmn-Hant', normalize='macro'))
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
    logger.info("Input: %s", tag)
    logger.info("Components: %s", components)

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
            if normalize and value in NORMALIZED_LANGUAGES:
                replacement = NORMALIZED_LANGUAGES[value]
                # parse the replacement if necessary -- this helps with
                # Serbian and Moldovan
                meaning.update(tag_to_meaning(replacement, normalize))
            elif normalize == 'macro' and value in NORMALIZED_MACROLANGUAGES:
                meaning[typ] = NORMALIZED_MACROLANGUAGES[value]
            else:
                meaning[typ] = value
        elif typ == 'region':
            if normalize and value in NORMALIZED_REGIONS:
                meaning[typ] = NORMALIZED_REGIONS[value]
            else:
                meaning[typ] = value
        else:
            meaning[typ] = value
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
        if SUPPRESSED_SCRIPTS.get(meaning['language']) == meaning['script']:
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
            copied['script'] = SUPPRESSED_SCRIPTS[lang]
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

