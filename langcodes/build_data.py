import marisa_trie
import json
import sys
import os
from pathlib import Path
from collections import defaultdict, Counter

import langcodes
from langcodes.util import data_filename
from langcodes.names import normalize_name
from langcodes.language_lists import CLDR_LANGUAGES
from langcodes.registry_parser import parse_registry

# Naming things is hard, especially languages
# ===========================================
#
# CLDR is supposed to avoid ambiguous language names, particularly among its
# core languages. But it seems that languages are incompletely disambiguated.
#
# It's convenient to be able to get a language by its name, without having to
# also refer to the language that the name is in. In most cases, we can do this
# unambiguously. With the disambiguations and overrides here, this will work
# in a lot of cases. However, some names such as 'Dongo', 'Fala', 'Malayo', and
# 'Tonga' are ambiguous in ways that can only be disambiguated by specifying
# the language the name is in.
#
# Ambiguous names can arise from:
#
# - Ambiguities in the scope of a name. These tend to span languages, and the
#   data files mask the fact that these names are generally ambiguous *within*
#   a language. And this is why we have codes.
#
# - Names that just happen to be ambiguous between different things with
#   different etymologies.
#
# Most doubly-claimed language names have standard ways to disambiguate
# them in CLDR, but names such as 'Tonga' and 'Fala' have complex
# inter-language ambiguities.
#
# Our approach is:
#
# - Fix conflicts that seem to arise simply from errors in the data, by
#   overriding the data.
#
# - Fix ambiguities in scope by preferring one scope over another. For example,
#   "North America" could refer to a region that includes Central America or
#   a region that doesn't. In any such conflict, we choose to include Central
#   America.
#
# - Avoid ambiguities between different sources of data, by using an order
#   of precedence. CLDR data takes priority over IANA data, which takes priority
#   over Wiktionary data.
#
# - When ambiguity remains, that name is not resolvable to a language code.
#   Resolving the name might require a more specific name, or specifying the
#   language that the name is in.


AMBIGUOUS_PREFERENCES = {
    # Prefer 'Micronesia' to refer to the Federated States of Micronesia -
    # this seems to be poorly disambiguated in many languages, but we can't
    # do much with a code for the general region of Micronesia
    'FM': {'057'},

    # Prefer region 003 for 'North America', which includes Central America
    # and the Caribbean, over region 021, which excludes them
    '003': {'021'},

    # Prefer region 005 for 'Lulli-Amerihkká' (South America), over region
    # 419, which includes Central America
    '005': {'419'},

    # Prefer 'Swiss German' to be a specific language
    'gsw': {'de-CH'},

    # Of the two countries named 'Congo', prefer the one with Kinshasa
    'CD': {'CG'},

    # Prefer Han script to not include bopomofo
    'Hani': {'Hanb'},

    # Prefer the specific language Tagalog over standard Filipino, because
    # the ambiguous name was probably some form of 'Tagalog'
    'tl': {'fil'},

    # Prefer Central Atlas Tamazight over Standard Moroccan Tamazight
    'tzm': {'zgh'},

    # Prefer the specific definition of Low Saxon
    'nds-NL': {'nds'},

    # Prefer the specific definition of Mandarin Chinese
    'cmn': {'zh'},

    # Prefer the regionally-specific definition of Dari
    'fa-AF': {'prs', 'fa'},

    # Ambiguity in the scope of Korean script (whether to include Han characters)
    'Kore': {'Hang'},
}

OVERRIDES = {
    # When I ask Wiktionary, it tells me that "Breatnais" is Scots Gaelic for
    # Welsh, not Breton, which is "Breatannais". This may be one of those
    # things that's not as standardized as it sounds, but let's at least agree
    # with Wiktionary and avoid a name conflict.
    ("gd", "br"): "Breatannais",

    # 'tagaloga' should be 'tl', not 'fil'
    ("eu", "tl"): "Tagaloga",
    ("eu", "fil"): "Filipinera",

    # 'Dakota' should be 'dak', not 'dar', which is "Dargwa"
    ("af", "dar"): "Dargwa",
    ("af-NA", "dar"): "Dargwa",

    # 'интерлингве' should be 'ie', not 'ia', which is 'интерлингва'
    ("az-Cyrl", "ia"): "интерлингва",

    # Don't confuse Samaritan Hebrew with Samaritan Aramaic
    ("en", "smp"): "Samaritan Hebrew",

    # Don't confuse the Mongol language of New Guinea with Mongolian
    ("en", "mgt"): "Mongol (New Guinea)",

    # Don't confuse Romang with Romani over the name 'Roma'
    ("en", "rmm"): "Romang",

    # 'Tai' is a large language family, and it should not refer exclusively and
    # unrelatedly to a language spoken by 900 people in New Guinea
    ("en", "taw"): "Kalam-Tai",

    # The code for Ladin -- the language that's almost certainly being named in
    # Friulian here -- is "lld". The given code of "lad" seems to be an error,
    # pointing to the Judeo-Spanish language Ladino, which would be less likely
    # to be what you mean when speaking Friulian.
    ("fur", "lad"): None
}


def resolve_name(key, vals, debug=False):
    """
    Given a name, and a number of possible values it could resolve to,
    find the single value it should resolve to, in the following way:

    - Apply the priority order
    - If names with the highest priority all agree, use that name
    - If there is disagreement that can be resolved by AMBIGUOUS_PREFERENCES,
      use that
    - Otherwise, don't resolve the name (and possibly show a debugging message
      when building the data)
    """
    max_priority = max([val[2] for val in vals])
    val_count = Counter([val[1] for val in vals if val[2] == max_priority])
    if len(val_count) == 1:
        unanimous = val_count.most_common(1)
        return unanimous[0][0]

    for pkey in val_count:
        if pkey in AMBIGUOUS_PREFERENCES:
            others = set(val_count)
            others.remove(pkey)
            if others == others & AMBIGUOUS_PREFERENCES[pkey]:
                if debug:
                    print("Resolved: {} -> {}".format(key, pkey))
                return pkey

    # In debug mode, show which languages vote for which name
    if debug and max_priority >= 0:
        votes = defaultdict(list)
        for voter, val, prio in vals:
            if prio == max_priority:
                votes[val].append(voter)

        print("{}:".format(key))
        for val, voters in sorted(votes.items()):
            print("\t{}: {}".format(val, ' '.join(voters)))

    # Don't use names that remain ambiguous
    return None


def resolve_names(name_dict, debug=False):
    resolved = {}
    for key, vals in sorted(name_dict.items()):
        resolved_name = resolve_name(key, vals, debug=debug)
        if resolved_name is not None:
            resolved[key] = resolved_name
    return resolved


def read_cldr_names(path, language, category):
    """
    Read CLDR's names for things in a particular language.
    """
    filename = data_filename('{}/{}/{}.json'.format(path, language, category))
    fulldata = json.load(open(filename, encoding='utf-8'))
    data = fulldata['main'][language]['localeDisplayNames'][category]
    return data


def read_cldr_supplemental(path, dataname):
    filename = data_filename('{}/supplemental/{}.json'.format(path, dataname))
    fulldata = json.load(open(filename, encoding='utf-8'))
    if dataname == 'aliases':
        data = fulldata['supplemental']['metadata']['alias']
    else:
        data = fulldata['supplemental'][dataname]
    return data


def read_cldr_name_file(path, langcode, category):
    data = read_cldr_names(path, langcode, category)
    name_quads = []
    for subtag, name in sorted(data.items()):
        if (langcode, subtag) in OVERRIDES:
            name = OVERRIDES[langcode, subtag]
            if name is None:
                continue

        if subtag == name:
            # Default entries that map a language code to itself, which
            # a lazy annotator just left there
            continue

        # CLDR assigns multiple names to one code by adding -alt-* to
        # the end of the code. For example, the English name of 'az' is
        # Azerbaijani, but the English name of 'az-alt-short' is Azeri.
        if normalize_name(name) == normalize_name(subtag):
            # Giving the name "zh (Hans)" to "zh-Hans" is still lazy
            continue

        priority = 3
        if '-alt-' in subtag:
            subtag, _ = subtag.split('-alt-', 1)
            priority = 1

        name_quads.append((langcode, subtag, name, priority))
    return name_quads


def read_iana_registry_names():
    language_quads = []
    script_quads = []
    region_quads = []
    for entry in parse_registry():
        target = None
        if entry['Type'] == 'language':
            target = language_quads
        elif entry['Type'] == 'script':
            target = script_quads
        elif entry['Type'] == 'region':
            target = region_quads
        if target is not None:
            subtag = entry['Subtag']
            priority = 2
            if 'Deprecated' in entry:
                priority = 0
            if ('en', subtag) in OVERRIDES:
                target.append(
                    ('en', subtag, OVERRIDES['en', subtag], priority)
                )
            else:
                for desc in entry['Description']:
                    target.append(
                        ('en', subtag, desc, priority)
                    )
    return language_quads, script_quads, region_quads


def read_iana_registry_scripts():
    scripts = {}
    for entry in parse_registry():
        if entry['Type'] == 'language' and 'Suppress-Script' in entry:
            scripts[entry['Subtag']] = entry['Suppress-Script']
    return scripts


def read_iana_registry_macrolanguages():
    macros = {}
    for entry in parse_registry():
        if entry['Type'] == 'language' and 'Macrolanguage' in entry:
            macros[entry['Subtag']] = entry['Macrolanguage']
    return macros


def read_iana_registry_replacements():
    replacements = {}
    for entry in parse_registry():
        if entry['Type'] == 'language' and 'Preferred-Value' in entry:
            # Replacements for language codes
            replacements[entry['Subtag']] = entry['Preferred-Value']
        elif 'Tag' in entry and 'Preferred-Value' in entry:
            # Replacements for entire tags
            replacements[entry['Tag'].lower()] = entry['Preferred-Value']
    return replacements


def read_csv_names(filename):
    data = open(filename, encoding='utf-8')
    quads = []
    for line in data:
        quad = line.rstrip().split(',', 3) + [True]
        quads.append(tuple(quad))
    return quads


def read_wiktionary_names(filename, language):
    data = open(filename, encoding='utf-8')
    quads = []
    for line in data:
        parts = line.rstrip().split('\t')
        code = parts[0]
        quads.append((language, code, parts[1], -1))
        names = [parts[1]]
        if len(parts) > 4 and parts[4]:
            names = parts[4].split(', ')
            for name in names:
                quads.append((language, code, name, -2))
    return quads


def update_names(names_fwd, names_rev, name_quads):
    for name_language, referent, name, priority in name_quads:
        # Get just the language from name_language, not the region or script.
        short_language = langcodes.get(name_language).language
        rev_all = names_rev.setdefault('und', {})
        rev_language = names_rev.setdefault(short_language, {})
        for rev_dict in (rev_all, rev_language):
            rev_dict.setdefault(normalize_name(name), []).append((name_language, referent, priority))

        fwd_key = '{}@{}'.format(referent.lower(), name_language)
        if fwd_key not in names_fwd:
            names_fwd[fwd_key] = name


def save_trie(mapping, filename):
    trie = marisa_trie.BytesTrie(
        (key, value.encode('utf-8')) for (key, value) in sorted(mapping.items())
    )
    trie.save(filename)


def save_reverse_name_tables(category, rev_dict):
    for language, lang_dict in rev_dict.items():
        if language in CLDR_LANGUAGES or language == 'und':
            os.makedirs(data_filename('trie/{}'.format(language)), exist_ok=True)
            save_trie(
                resolve_names(lang_dict, debug=True),
                data_filename('trie/{}/name_to_{}.marisa'.format(language, category))
            )


def build_tries(cldr_path):
    language_names_rev = {}
    region_names_rev = {}
    script_names_rev = {}
    language_names_fwd = {}
    region_names_fwd = {}
    script_names_fwd = {}
    cldr_main_path = Path(cldr_path) / 'main'

    for subpath in sorted(cldr_main_path.iterdir()):
        if subpath.is_dir():
            langcode = subpath.name
            if (subpath / 'languages.json').exists():
                language_data = read_cldr_name_file(cldr_main_path, langcode, 'languages')
                update_names(language_names_fwd, language_names_rev, language_data)

                script_data = read_cldr_name_file(cldr_main_path, langcode, 'scripts')
                update_names(script_names_fwd, script_names_rev, script_data)

                region_data = read_cldr_name_file(cldr_main_path, langcode, 'territories')
                update_names(region_names_fwd, region_names_rev, region_data)

    iana_languages, iana_scripts, iana_regions = read_iana_registry_names()
    update_names(language_names_fwd, language_names_rev, iana_languages)
    update_names(script_names_fwd, script_names_rev, iana_scripts)
    update_names(region_names_fwd, region_names_rev, iana_regions)

    wiktionary_data = read_wiktionary_names(data_filename('wiktionary/codes-en.csv'), 'en')
    update_names(language_names_fwd, language_names_rev, wiktionary_data)

    extra_language_data = read_csv_names(data_filename('extra_language_names.csv'))
    update_names(language_names_fwd, language_names_rev, extra_language_data)

    save_reverse_name_tables('language', language_names_rev)
    save_reverse_name_tables('script', script_names_rev)
    save_reverse_name_tables('region', region_names_rev)
    save_trie(language_names_fwd, data_filename('trie/language_to_name.marisa'))
    save_trie(script_names_fwd, data_filename('trie/script_to_name.marisa'))
    save_trie(region_names_fwd, data_filename('trie/region_to_name.marisa'))


def write_python_dict(outfile, name, d):
    print("%s = {" % name, file=outfile)
    for key in sorted(d):
        print("    %r: %r," % (key, d[key]), file=outfile)
    print("}", file=outfile)


GENERATED_HEADER = "# This file is generated by build_data.py."


def build_dicts(cldr_supp_path):
    lang_scripts = read_iana_registry_scripts()
    macrolanguages = read_iana_registry_macrolanguages()
    iana_replacements = read_iana_registry_replacements()

    alias_data = read_cldr_supplemental(cldr_supp_path, 'aliases')
    likely_subtags = read_cldr_supplemental(cldr_supp_path, 'likelySubtags')
    replacements = {}
    norm_macrolanguages = {}
    for alias_type in ['languageAlias', 'scriptAlias', 'territoryAlias']:
        aliases = alias_data[alias_type]
        # Initially populate 'languageAlias' with the aliases from the IANA file
        if alias_type == 'languageAlias':
            replacements[alias_type] = iana_replacements
            replacements[alias_type]['root'] = 'und'
        else:
            replacements[alias_type] = {}
        for code, value in aliases.items():
            # Make all keys lowercase so they can be looked up
            # case-insensitively
            code = code.lower()

            # If there are multiple replacements, take the first one. For example,
            # we just replace the Soviet Union (SU) with Russia (RU), instead of
            # trying to do something context-sensitive and poorly standardized
            # that selects one of the successor countries to the Soviet Union.
            replacement = value['_replacement'].split()[0]
            if value['_reason'] == 'macrolanguage':
                norm_macrolanguages[code] = replacement
            else:
                replacements[alias_type][code] = replacement

    with open('data_dicts.py', 'w', encoding='utf-8') as outfile:
        print(GENERATED_HEADER, file=outfile)
        write_python_dict(outfile, 'DEFAULT_SCRIPTS', lang_scripts)
        write_python_dict(outfile, 'LANGUAGE_REPLACEMENTS', replacements['languageAlias'])
        write_python_dict(outfile, 'SCRIPT_REPLACEMENTS', replacements['scriptAlias'])
        write_python_dict(outfile, 'REGION_REPLACEMENTS', replacements['territoryAlias'])
        write_python_dict(outfile, 'MACROLANGUAGES', macrolanguages)
        write_python_dict(outfile, 'NORMALIZED_MACROLANGUAGES', norm_macrolanguages)
        write_python_dict(outfile, 'LIKELY_SUBTAGS', likely_subtags)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: build_data.py <path to CLDR name data> <path to CLDR supplemental data>")
        sys.exit(1)
    build_dicts(sys.argv[2])
    build_tries(sys.argv[1])
