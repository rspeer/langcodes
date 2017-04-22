import marisa_trie
import json
from pathlib import Path
from collections import defaultdict, Counter

from langcodes.util import data_filename
from langcodes.names import normalize_name
from langcodes.registry_parser import parse_registry


# CLDR is supposed to avoid ambiguous language names, particularly among its
# core languages. But there is no complete solution to this problem.
#
# While it may seem like a solid plan to separate language names by the
# language they are being named in, for the types of names that conflict, this
# would often simply hide the problem under each annotator's arbitrary
# decisions about what a name means.
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
# them in CLDR, but names such as 'Tonga' and 'Sango' have complex
# inter-language ambiguities.
#
# Our approach is:
#
# - Fix conflicts that seem to arise simply from errors in the data, by
#   overriding the data
#
# - Fix ambiguities in scope by preferring one scope over another. For example,
#   "North America" could refer to a region that includes Central America or
#   a region that doesn't. In any such conflict, we choose to include Central
#   America.
#
# - When ambiguity remains, that name is not resolvable to a language code.
#   Every official English name in the CLDR, as well as the vast majority of
#   other names, can be resolved. An ambiguous name such as 'Tonga' can be
#   resolved by using a different name ("Tongan" or "Tonga Nyasa").


AMBIGUOUS_PREFERENCES = {
    # Prefer 'America' to be the United States when ambiguous. Yes, this is
    # overly specific in some languages (such as Spanish), but in other
    # languages (such as Hindi) it's correct.
    #
    # When dealing with language codes, it seems unlikely that there would
    # be a need to get a code referring to the two continents of the Americas,
    # and to expect to find it under a vague name like 'America'.
    'US': {'019'},

    # Prefer 'Micronesia' to be the Federated States of Micronesia, not the
    # geographical region, by similar reasoning to 'America'
    'FM': {'057'},

    # Prefer region 003 for 'North America', which includes Central America
    # and the Caribbean, over region 021, which excludes them
    '003': {'021'},

    # Prefer 'Swiss German' to be a specific language
    'gsw': {'de-CH'},

    # Of the two countries named 'Congo', prefer the one with Kinshasa
    'CD': {'CG'},

    # Prefer Han script to not include bopomofo
    'Hani': {'Hanb'},

    # Prefer Umbundu over Kimbundu for the name 'Mbundu'
    'umb': {'kmb'},

    # Prefer village Kwasio over nomadic Gyele (some sources consider them
    # dialects of the same language)
    'nmg': {'gyi'},

    # Prefer Kinyarwanda over Rwa
    'rw': {'rwk'},

    # Can't tell why Catalan says Bulu is named "Seki", but let's keep Bulu
    # and Seki separate
    'syi': {'bum'},

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
    'fa-AF': {'prs'},

    # Flemish: specific
    'nl-BE': {'nl'},

    # Moldovan: specific
    'ro-MD': {'ro'},

    # Congo Swahili: define it as a region, as it's only listed as a separate
    # language in the IANA file
    'sw-CD': {'swc'},

    # Prefer the macrolanguage for Pulaar
    'ff': {'fuc'},

    # Prefer the macrolanguage for Tamasheq
    'tmh': {'taq'},

    # 'Kiswahili' is Swahili for Swahili
    'sw': {'swh'},

    # Chinook
    'chn': {'chh'},

    # Korean script (including Han)
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

    # 'لتونی' is Persian for "Latvia". Is it really also Mazanderani for
    # "Lithuania"? This seems unlikely, given that Mazanderani is closely
    # related to Persian. But as Mazanderani is far from a core language, we
    # fix the immediate problem by just removing its name for Lithuania.
    ("mzn", "lt"): None,
    ("mzn", "LT"): None,

    # Hungarian seems to have "Ilokano" where it should have a name for
    # Hiligaynon, a different language from Ilokano
    ("hu", "hil"): None,

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
    val_count = Counter([val[1] for val in vals])
    if len(val_count) == 1:
        unanimous = val_count.most_common(1)
        return unanimous[0][0]

    for pkey in val_count:
        if pkey in AMBIGUOUS_PREFERENCES:
            if debug:
                print("Resolved: {} -> {}".format(key, pkey))
            return pkey

    # In debug mode, show which languages vote for which name
    if debug:
        votes = defaultdict(list)
        for voter, val in vals:
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


def read_cldr_names(language, category):
    """
    Read CLDR's names for things in a particular language.
    """
    filename = data_filename('cldr/main/{}/{}.json'.format(language, category))
    fulldata = json.load(open(filename, encoding='utf-8'))
    data = fulldata['main'][language]['localeDisplayNames'][category]
    return data


def read_cldr_supplemental(dataname):
    filename = data_filename('cldr/supplemental/{}.json'.format(dataname))
    fulldata = json.load(open(filename, encoding='utf-8'))
    if dataname == 'aliases':
        data = fulldata['supplemental']['metadata']['alias']
    else:
        data = fulldata['supplemental'][dataname]
    return data


def read_cldr_name_file(langcode, category):
    data = read_cldr_names(langcode, category)
    name_triples = []
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

        if '-alt-' in subtag:
            subtag, _ = subtag.split('-alt-', 1)

        name_triples.append((langcode, subtag, name))
    return name_triples


def read_iana_registry_names():
    language_triples = []
    script_triples = []
    region_triples = []
    for entry in parse_registry():
        target = None
        if entry['Type'] == 'language':
            target = language_triples
        elif entry['Type'] == 'script':
            target = script_triples
        elif entry['Type'] == 'region':
            target = region_triples
        if target is not None and 'Deprecated' not in entry:
            subtag = entry['Subtag']
            if ('en', subtag) in OVERRIDES:
                target.append(
                    ('en', subtag, OVERRIDES['en', subtag])
                )
            else:
                for desc in entry['Description']:
                    target.append(
                        ('en', subtag, desc)
                    )
    return language_triples, script_triples, region_triples


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
    triples = []
    for line in data:
        triple = line.rstrip().split(',', 3)
        triples.append(triple)
    return triples


def read_wiktionary_names(filename, language):
    data = open(filename, encoding='utf-8')
    triples = []
    for line in data:
        parts = line.rstrip().split('\t')
        code = parts[0]
        names = [parts[1]]
        #if len(parts) > 4 and parts[4]:
        #    names.extend(parts[4].split(', '))
        for name in names:
            triples.append((language, code, name))
    return triples


def update_names(names_fwd, names_rev, name_triples):
    for name_language, referent, name in name_triples:
        names_rev.setdefault(normalize_name(name), []).append((name_language, referent))
        fwd_key = '{}@{}'.format(referent.lower(), name_language)
        if fwd_key not in names_fwd:
            names_fwd[fwd_key] = name


def save_trie(mapping, filename):
    trie = marisa_trie.BytesTrie(
        (key, value.encode('utf-8')) for (key, value) in sorted(mapping.items())
    )
    trie.save(filename)


def build_tries():
    language_names_rev = defaultdict(list)
    region_names_rev = defaultdict(list)
    script_names_rev = defaultdict(list)
    language_names_fwd = {}
    region_names_fwd = {}
    script_names_fwd = {}

    cldr_path = Path(data_filename('cldr/main'))
    for subpath in sorted(cldr_path.iterdir()):
        if subpath.is_dir():
            langcode = subpath.name
            if (subpath / 'languages.json').exists():
                language_data = read_cldr_name_file(langcode, 'languages')
                update_names(language_names_fwd, language_names_rev, language_data)

                script_data = read_cldr_name_file(langcode, 'scripts')
                update_names(script_names_fwd, script_names_rev, script_data)

                region_data = read_cldr_name_file(langcode, 'territories')
                update_names(region_names_fwd, region_names_rev, region_data)

    iana_languages, iana_scripts, iana_regions = read_iana_registry_names()
    update_names(language_names_fwd, language_names_rev, iana_languages)
    update_names(script_names_fwd, script_names_rev, iana_scripts)
    update_names(region_names_fwd, region_names_rev, iana_regions)

    wiktionary_data = read_wiktionary_names(data_filename('wiktionary/codes-en.csv'), 'en')
    update_names(language_names_fwd, language_names_rev, wiktionary_data)

    extra_language_data = read_csv_names(data_filename('extra_language_names.csv'))
    update_names(language_names_fwd, language_names_rev, extra_language_data)

    save_trie(
        resolve_names(language_names_rev, debug=True),
        data_filename('trie/name_to_language.marisa')
    )
    save_trie(
        resolve_names(region_names_rev, debug=True),
        data_filename('trie/name_to_region.marisa')
    )
    save_trie(
        resolve_names(script_names_rev, debug=True),
        data_filename('trie/name_to_script.marisa')
    )
    save_trie(language_names_fwd, data_filename('trie/language_to_name.marisa'))
    save_trie(script_names_fwd, data_filename('trie/script_to_name.marisa'))
    save_trie(region_names_fwd, data_filename('trie/region_to_name.marisa'))


def write_python_dict(outfile, name, d):
    print("%s = {" % name, file=outfile)
    for key in sorted(d):
        print("    %r: %r," % (key, d[key]), file=outfile)
    print("}", file=outfile)


GENERATED_HEADER = "# This file is generated by build_data.py."


def build_dicts():
    lang_scripts = read_iana_registry_scripts()
    macrolanguages = read_iana_registry_macrolanguages()
    iana_replacements = read_iana_registry_replacements()

    alias_data = read_cldr_supplemental('aliases')
    likely_subtags = read_cldr_supplemental('likelySubtags')
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
    build_dicts()
    build_tries()
