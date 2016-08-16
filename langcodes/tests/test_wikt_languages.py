"""
Here, we test that we can associate a language code with each language name
that is commonly used on Wiktionary, and that all the language codes are
different.
"""
import langcodes
from langcodes.wiktionary_language_list import LANGUAGE_NAMES


def check_wiktionary_language(target_lang):
    seen_codes = {}
    for lang_name in LANGUAGE_NAMES[target_lang]:
        if lang_name.startswith('Proto-'):
            lang_name = lang_name[6:]
        code = str(langcodes.find(lang_name, target_lang))
        assert code not in seen_codes, \
            "%r and %r have the same code" % (seen_codes[code], lang_name)
        seen_codes[code] = lang_name


def test_wiktionary_languages():
    yield check_wiktionary_language, 'en'
    yield check_wiktionary_language, 'de'
