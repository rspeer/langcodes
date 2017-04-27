import json
import marisa_trie
import warnings

import langcodes
from langcodes.util import data_filename


TRIES = {}


def normalize_name(name):
    """
    When looking up a language-code component by name, we would rather ignore
    distinctions of case and certain punctuation. "Chinese (Traditional)"
    should be matched by "Chinese Traditional" and "chinese traditional".
    """
    name = name.casefold()
    name = name.replace("’", "'")
    name = name.replace("-", " ")
    name = name.replace("(", "")
    name = name.replace(")", "")
    name = name.replace(",", "")
    return name.strip()


def load_trie(filename):
    """
    Load a BytesTrie from the marisa_trie on-disk format.
    """
    trie = marisa_trie.BytesTrie()
    # marisa_trie raises warnings that make no sense. Ignore them.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        trie.load(filename)
    return trie


def get_trie_value(trie, key):
    """
    Get the value that a BytesTrie stores for a particular key, decoded
    as Unicode. Raises a KeyError if there is no value for that key.
    """
    return trie[key][0].decode('utf-8')


def name_to_code(category, name, language: str='und'):
    """
    Get a language, script, or region by its name in some language.

    The language here must be a string representing a language subtag only.
    The `Language.find` method can handle other representations of a language
    and normalize them to this form.

    The default language, "und", will allow matching names in any language,
    so you can get the code 'fr' by looking up "French", "Français", or
    "francés".

    A small amount of fuzzy matching is supported: if the name can be
    shortened or lengthened to match a single language name, you get that
    language. This allows, for example, "Hakka Chinese" to match "Hakka".

    Occasionally, names are ambiguous in a way that can be resolved by
    specifying what name the language is supposed to be in. For example,
    there is a language named 'Malayo' in English, but it's different from
    the language named 'Malayo' in Spanish (which is Malay). Specifying the
    language will look up the name in a trie that is only in that language.
    """
    assert '/' not in language, "Language codes cannot contain slashes"
    assert '-' not in language, "This code should be reduced to a language subtag only"
    trie_name = '{}/name_to_{}'.format(language, category)
    if trie_name not in TRIES:
        TRIES[trie_name] = load_trie(data_filename('trie/{}.marisa'.format(trie_name)))

    trie = TRIES[trie_name]
    lookup = normalize_name(name)
    if lookup in trie:
        return get_trie_value(trie, lookup)
    else:
        # Is this a language plus extra junk? Maybe it has "...isch", "... language",
        # or "... Chinese" attached to it, for example.
        prefixes = trie.prefixes(lookup)
        if prefixes and len(prefixes[-1]) >= 4:
            return get_trie_value(trie, prefixes[-1])
        else:
            return None


def code_to_names(category, code):
    """
    Given the code for a language, script, or region, get a dictionary of its
    names in various languages.
    """
    trie_name = '{}_to_name'.format(category)
    if trie_name not in TRIES:
        TRIES[trie_name] = load_trie(data_filename('trie/{}.marisa'.format(trie_name)))

    trie = TRIES[trie_name]
    lookup = code.lower() + '@'
    possible_keys = trie.keys(lookup)
    names = {}
    for key in possible_keys:
        target_language = key.split('@')[1]
        names[target_language] = get_trie_value(trie, key)
    return names
