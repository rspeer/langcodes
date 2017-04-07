import marisa_trie
import json
from langcodes.util import data_filename
from pathlib import Path
from collections import defaultdict, Counter


# CLDR is supposed to avoid ambiguous language names, particularly among its
# core languages. There are a few that we have to fix.
#
# These amount to:
#
# - Ambiguities in the scope of a name. These tend to span languages, and the
#   data files mask the fact that these names are generally ambiguous *within*
#   a language. And this is why we have codes.
#
#   These names include:
#
#   - "America" (019 or US)
#   - "North America" (003 or 021)
#   - "Micronesia" (057 or FM)
#   - "Congo" (CD or CG)
#   - "Swiss German" (de-CH or gsw)
#   - "Tagalog" and "Filipino" (tl or fil)
#   - "Mbundu" (umb or kmb)
#   - "Tamazight" (tzm or zgh)
#
# - Names that just happen to be ambiguous between different things with
#   with different etymologies, such as 'Tonga'.


AMBIGUOUS_PREFERENCES = {
    # Prefer America to be the United States when ambiguous (it literally
    # means this in some languages, and there are other words for the Americas)
    'US': {'019'},

    # Prefer Micronesia to be the Federated States of Micronesia
    'FM': {'057'},

    # Prefer to exclude the Caribbean from North America
    '003': {'021'},

    # Prefer Swiss German to be a specific language
    'gsw': {'de-CH'},

    # Of the two countries named 'Congo', prefer the one with Kinshasa
    'CD': {'CG'},

    # Prefer Han script to not include bopomofo
    'Hani': {'Hanb'},

    # 'Tonga' could be Tongan, the language of Tonga, or it could be one of
    # three African languages that also have other names. When ambiguous,
    # prefer Tongan.
    'to': {'tog', 'toh', 'toi'},

    # 'Sango' is the primary language of the Central African Republic. In
    # some languages, this is ambiguous with 'Sangu', which is one of two
    # other languages.
    'sg': {'sbp', 'snq'},

    # Prefer Umbundu over Kimbundu for the name 'Mbundu'
    'umb': {'kmb'},

    # Prefer Kinyarwanda over Rwa
    'rw': {'rwk'},

    # Prefer the specific language Tagalog over standard Filipino, because
    # the ambiguous name was probably some form of 'Tagalog'
    'tl': {'fil'},

    # Prefer Central Atlas Tamazight over Standard Moroccan Tamazight
    'tzm': {'zgh'},
}

OVERRIDES = {
    # "Breatnais" is Scots Gaelic for Welsh, not Breton, which is "Breatannais"
    ("gd", "br"): "Breatannais",

    # 'tagaloga' should be 'tl', not 'fil'
    ("eu", "tl"): "Tagaloga",
    ("eu", "fil"): "Filipinera",

    # 'Dakota' should be 'dak', not 'dar', which is "Dargwa"
    ("af", "dar"): "Dargwa",
    ("af-NA", "dar"): "Dargwa",

    # No evidence that language 'ssy' is called "саха" in Belarusian, and that
    # name belongs to 'sah'
    ("be", "ssy"): "сахо",

    # 'интерлингве' should be 'ie', not 'ia', which is 'интерлингва'
    ("az-Cyrl", "ia"): "интерлингва",

    # Is the name 'Letoni' really ambiguous between Lithuania and Latvia?
    ("mzn", "lt"): None,
    ("mzn", "LT"): None,
}


def normalize_name(name):
    name = name.casefold()
    name = name.replace("’", "'")
    name = name.replace("-", " ")
    name = name.replace("(", "")
    name = name.replace(")", "")
    name = name.replace(",", "")
    return name


def resolve_name(key, vals, debug=False):
    val_count = Counter([val[0] for val in vals])
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
        for val, voter in vals:
            votes[val].append(voter)

        print("{}:".format(key))
        for val, voters in sorted(votes.items()):
            print("\t{}: {}".format(val, ' '.join(voters)))

    # Popularity contest
    top_two = val_count.most_common(2)

    # Make sure there isn't a tie
    if len(top_two) == 2:
        assert (top_two[0][1] != top_two[1][1]), top_two

    # Use the unique most common value
    return top_two[0][0]


def resolve_names(name_dict, debug=False):
    resolved = {}
    for key, vals in sorted(name_dict.items()):
        resolved[key] = resolve_name(key, vals, debug=debug)
    return resolved


def load_cldr_name_file(typ, name_fwd, name_rev, langcode, path):
    fulldata = json.load(path.open(encoding='utf-8'))
    data = fulldata['main'][langcode]['localeDisplayNames'][typ]
    for subtag, name in data.items():
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
        name_norm = normalize_name(name)
        if name_norm == normalize_name(subtag):
            # Giving the name "zh (Hans)" to "zh-Hans" is still lazy
            continue

        if '-alt-' in subtag:
            subtag, _ = subtag.split('-alt-', 1)
        if subtag not in name_fwd:
            name_fwd[subtag.casefold()] = name
        name_rev[name_norm].append((subtag, langcode))


def make_trie(mapping):
    trie = marisa_trie.BytesTrie(
        (key, value.encode('utf-8')) for (key, value) in mapping.items()
    )
    return trie


def build_data():
    language_names = {}
    language_names_rev = defaultdict(list)
    region_names = {}
    region_names_rev = defaultdict(list)
    script_names = {}
    script_names_rev = defaultdict(list)
    language_replacements = {}
    region_replacements = {}

    cldr_path = Path(data_filename('cldr/main'))
    for subpath in sorted(cldr_path.iterdir()):
        if subpath.is_dir():
            langcode = subpath.name
            if (subpath / 'languages.json').exists():
                load_cldr_name_file(
                    'languages', language_names, language_names_rev,
                    langcode, subpath / 'languages.json'
                )
            if (subpath / 'territories.json').exists():
                load_cldr_name_file(
                    'territories', region_names, region_names_rev,
                    langcode, subpath / 'territories.json'
                )
            if (subpath / 'scripts.json').exists():
                load_cldr_name_file(
                    'scripts', script_names, script_names_rev,
                    langcode, subpath / 'scripts.json'
                )

    language_name_trie = make_trie(resolve_names(language_names_rev, debug=True))
    language_name_trie.save(data_filename('trie/language_names.marisa'))

    region_name_trie = make_trie(resolve_names(region_names_rev, debug=True))
    region_name_trie.save(data_filename('trie/region_names.marisa'))

    script_name_trie = make_trie(resolve_names(script_names_rev, debug=True))
    script_name_trie.save(data_filename('trie/script_names.marisa'))


if __name__ == '__main__':
    build_data()
