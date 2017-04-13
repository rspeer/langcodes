import marisa_trie
import json
from langcodes.util import data_filename
from langcodes.cldr import OVERRIDES, normalize_name, read_cldr_names
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
#   different etymologies. Most of these have standard ways to disambiguate
#   them in CLDR, but names such as 'Tonga' and 'Sango' have complex
#   inter-language ambiguities.


AMBIGUOUS_PREFERENCES = {
    # Prefer 'America' to be the United States when ambiguous. Yes, this is
    # overly specific in some languages (such as Spanish), but in other
    # languages (such as Hindi) it's correct.
    #
    # When dealing with language codes, it seems unlikely that there would
    # be a need to get a code referring to the two continents of the Americas,
    # and to expect to find it under a vague name like 'America'.
    'US': {'019'},

    # Prefer Micronesia to be the Federated States of Micronesia, by similar
    # reasoning to 'America'
    'FM': {'057'},

    # Prefer region 021 for 'North America', which includes Central America
    # and the Caribbean, over region 003, which excludes them
    '021': {'003'},

    # Prefer 'Swiss German' to be a specific language
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

# See also OVERRIDES in names.py.


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


def load_cldr_name_file(langcode, category):
    data = read_cldr_names(langcode, category)
    name_triples = []
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
        if normalize_name(name) == normalize_name(subtag):
            # Giving the name "zh (Hans)" to "zh-Hans" is still lazy
            continue

        if '-alt-' in subtag:
            subtag, _ = subtag.split('-alt-', 1)

        name_triples.append((langcode, subtag, name))
    return name_triples


def update_names(names_fwd, names_rev, name_triples):
    for name_language, referent, name in name_triples:
        names_rev.setdefault(normalize_name(name), []).append((name_language, referent))
        fwd_key = '{}@{}'.format(normalize_name(referent), name_language)
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
                language_data = load_cldr_name_file(langcode, 'languages')
                update_names(language_names_fwd, language_names_rev, language_data)

                script_data = load_cldr_name_file(langcode, 'scripts')
                update_names(script_names_fwd, script_names_rev, script_data)

                region_data = load_cldr_name_file(langcode, 'territories')
                update_names(region_names_fwd, region_names_rev, region_data)

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


if __name__ == '__main__':
    build_tries()
