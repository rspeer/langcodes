import json
from langcodes.util import data_filename


_DATA_CACHE = {}


OVERRIDES = {
    # "Breatnais" is Scots Gaelic for Welsh, not Breton, which is "Breatannais"
    ("gd", "br"): "Breatannais",

    # 'tagaloga' should be 'tl', not 'fil'
    ("eu", "tl"): "Tagaloga",
    ("eu", "fil"): "Filipinera",

    # 'Dakota' should be 'dak', not 'dar', which is "Dargwa"
    ("af", "dar"): "Dargwa",
    ("af-NA", "dar"): "Dargwa",

    # No evidence that language 'ssy' is called "саха" in Belarusian when it's
    # "Saho" in other languages; the name "саха" is already used for 'sah'
    ("be", "ssy"): "сахо",

    # 'интерлингве' should be 'ie', not 'ia', which is 'интерлингва'
    ("az-Cyrl", "ia"): "интерлингва",

    # 'لتونی' is Persian for "Latvia". Is it really also Mazanderani for
    # "Lithuania"? This seems unlikely, given that Mazanderani is closely
    # related to Persian. But as Mazanderani is far from a core language, we
    # fix the immediate problem by just removing its name for Lithuania.
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
    return name.strip()


def read_cldr_names(language, category):
    """
    Read CLDR's names for things in a particular language.
    """
    if (language, category) in _DATA_CACHE:
        return _DATA_CACHE[language, category]

    filename = data_filename('cldr/main/{}/{}.json'.format(language, category))
    fulldata = json.load(open(filename, encoding='utf-8'))
    data = fulldata['main'][language]['localeDisplayNames'][category]
    _DATA_CACHE[language, category] = data
    return data


def read_cldr_supplemental(dataname):
    cache_key = ('SUPP', dataname)
    if cache_key in _DATA_CACHE:
        return _DATA_CACHE[cache_key]

    filename = data_filename('cldr/supplemental/{}.json'.format(dataname))
    if dataname == 'aliases':
        dataname = 'alias'
    fulldata = json.load(open(filename, encoding='utf-8'))
    data = fulldata['supplemental'][dataname]
    _DATA_CACHE[cache_key] = data
    return data


def get_macrolanguage(language):
    aliases = read_cldr_supplemental('aliases')
    language_aliases = aliases['languageAlias']
    if language in language_aliases:
        entry = language_aliases[language]
        if entry['_reason'] == 'macrolanguage':
            return entry['_replacement']
    return language


def normalize_language(language, macro=True):
    aliases = read_cldr_supplemental('aliases')
    language_aliases = aliases['languageAlias']
    if language in language_aliases:
        entry = language_aliases[language]
        if macro or entry['_reason'] != 'macrolanguage':
            return entry['_replacement']
    return language


def normalize_region(region):
    aliases = read_cldr_supplemental('aliases')
    region_aliases = aliases['territoryAlias']
    if region in region_aliases:
        replacement = region_aliases[region]['_replacement']
        # Multiple replacements are something we can't handle
        return replacement.split(' ')[0]
    return region


def get_default_script(language):
    default_scripts = read_cldr_supplemental('')
