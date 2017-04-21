import json
import marisa_trie
import warnings

from langcodes.util import data_filename


TRIES = {}


def normalize_name(name):
    name = name.casefold()
    name = name.replace("’", "'")
    name = name.replace("-", " ")
    name = name.replace("(", "")
    name = name.replace(")", "")
    name = name.replace(",", "")
    return name.strip()


def load_trie(filename):
    trie = marisa_trie.BytesTrie()
    # marisa_trie raises warnings that make no sense. Ignore them.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        trie.load(filename)
    return trie


def get_trie_value(trie, key):
    return trie[key][0].decode('utf-8')


def name_to_code(category, name):
    trie_name = 'name_to_{}'.format(category)
    if trie_name not in TRIES:
        TRIES[trie_name] = load_trie(data_filename('trie/{}.marisa'.format(trie_name)))

    trie = TRIES[trie_name]
    lookup = normalize_name(name)
    if lookup in trie:
        return get_trie_value(trie, lookup)
    else:
        # Is this a language plus extra junk?
        prefixes = trie.prefixes(lookup)
        if prefixes and len(prefixes[-1]) >= 4:
            return get_trie_value(trie, prefixes[-1])
        else:
            # Is this an unambiguous prefix of a language?
            longer_keys = trie.keys(lookup)
            if 1 <= len(longer_keys) <= 20:
                possible_values = set([get_trie_value(trie, key) for key in longer_keys])
                if len(possible_values) == 1:
                    return possible_values.pop()
            else:
                return None


def code_to_names(category, code):
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
