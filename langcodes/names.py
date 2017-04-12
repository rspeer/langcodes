import json
from .util import data_filename


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
    return name


def read_cldr_names(language, category):
    """
    Read CLDR's names for things in a particular language.
    """
    filename = data_filename('cldr/main/{}/{}.json'.format(language, category))
    fulldata = json.load(open(filename, encoding='utf-8'))
    data = fulldata['main'][language]['localeDisplayNames'][category]
    return data



