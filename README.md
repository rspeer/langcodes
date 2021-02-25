# Langcodes: a library for language codes

**langcodes** knows what languages are. It knows the standardized codes that
refer to them, such as `en` for English, `es` for Spanish and `hi` for Hindi.
Often, it knows what these languages are called *in* a language, and that
language doesn't have to be English.

It may sound to you like langcodes solves a pretty boring problem. At one
level, that's right. Sometimes you have a boring problem, and it's great when a
library solves it for you.

But there's an interesting problem hiding in here. How do you work with
language codes? How do you know when two different codes represent the same
thing? How should your code represent relationships between codes, like the
following?

* `eng` is equivalent to `en`.
* `fra` and `fre` are both equivalent to `fr`.
* `en-GB` might be written as `en-gb` or `en_GB`. Or as 'en-UK', which is
  erroneous, but should be treated as the same.
* `en-CA` is not exactly equivalent to `en-US`, but it's really, really close.
* `en-Latn-US` is equivalent to `en-US`, because written English must be written
  in the Latin alphabet to be understood.
* The difference between `ar` and `arb` is the difference between "Arabic" and
  "Modern Standard Arabic", a difference that may not be relevant to you.
* You'll find Mandarin Chinese tagged as `cmn` on Wiktionary, but many other
  resources would call the same language `zh`.
* Chinese is written in different scripts in different territories. Some
  software distinguishes the script. Other software distinguishes the territory.
  The result is that `zh-CN` and `zh-Hans` are used interchangeably, as are
  `zh-TW` and `zh-Hant`, even though occasionally you'll need something
  different such as `zh-HK` or `zh-Latn-pinyin`.
* The Indonesian (`id`) and Malaysian (`ms` or `zsm`) languages are mutually
  intelligible.
* `jp` is not a language code. (The language code for Japanese is `ja`, but
  people confuse it with the country code for Japan.)

One way to know is to read IETF standards and Unicode technical reports.
Another way is to use a library that implements those standards and guidelines
for you, which langcodes does.

langcodes is maintained by Robyn Speer at [Luminoso](http://luminoso.com), and
is released as free software under the MIT license. Luminoso has [more free
software](https://github.com/LuminosoInsight). We're also [hiring
developers](https://www.luminoso.com/luminoso-careers).

## Standards implemented

Although this is not the only reason to use it, langcodes will make you more
acronym-compliant.

langcodes implements [BCP 47](http://tools.ietf.org/html/bcp47), the IETF Best
Current Practices on Tags for Identifying Languages. BCP 47 is also known as
RFC 5646. It subsumes standards such as ISO 639, and it also implements
recommendations from the [Unicode CLDR](http://cldr.unicode.org).

The package also comes with a database of language properties and names, built
from Unicode CLDR and the IANA subtag registry.

In summary, langcodes takes language codes and does the Right Thing with them,
and if you want to know exactly what the Right Thing is, there are some
documents you can go read.


# Documentation

## Standardizing language tags

This function standardizes tags, as strings, in several ways.

It replaces overlong tags with their shortest version, and also formats them
according to the conventions of BCP 47:

    >>> from langcodes import *
    >>> standardize_tag('eng_US')
    'en-US'

It removes script subtags that are redundant with the language:

    >>> standardize_tag('en-Latn')
    'en'

It replaces deprecated values with their correct versions, if possible:

    >>> standardize_tag('en-uk')
    'en-GB'

Sometimes this involves complex substitutions, such as replacing Serbo-Croatian
(`sh`) with Serbian in Latin script (`sr-Latn`), or the entire tag `sgn-US`
with `ase` (American Sign Language).

    >>> standardize_tag('sh-QU')
    'sr-Latn-EU'

    >>> standardize_tag('sgn-US')
    'ase'

If *macro* is True, it uses macrolanguage codes as a replacement for the most
common standardized language within that macrolanguage.

    >>> standardize_tag('arb-Arab', macro=True)
    'ar'

Even when *macro* is False, it shortens tags that contain both the
macrolanguage and the language:

    >>> standardize_tag('zh-cmn-hans-cn')
    'cmn-Hans-CN'

    >>> standardize_tag('zh-cmn-hans-cn', macro=True)
    'zh-Hans-CN'

If the tag can't be parsed according to BCP 47, this will raise a
LanguageTagError (a subclass of ValueError):

    >>> standardize_tag('spa-latn-mx')
    'es-MX'

    >>> standardize_tag('spa-mx-latn')
    Traceback (most recent call last):
        ...
    langcodes.tag_parser.LanguageTagError: This script subtag, 'latn', is out of place. Expected variant, extension, or end of string.


## Language objects

This package defines one class, named Language, which contains the results
of parsing a language tag. Language objects have the following fields,
any of which may be unspecified:

- *language*: the code for the language itself.
- *script*: the 4-letter code for the writing system being used.
- *territory*: the 2-letter or 3-digit code for the country or similar region
  whose usage of the language appears in this text.
- *extlangs*: a list of more specific language codes that follow the language
  code. (This is allowed by the language code syntax, but deprecated.)
- *variants*: codes for specific variations of language usage that aren't
  covered by the *script* or *territory* codes.
- *extensions*: information that's attached to the language code for use in
  some specific system, such as Unicode collation orders.
- *private*: a code starting with `x-` that has no defined meaning.

The `Language.get` method converts a string to a Language instance, and the
`Language.make` method makes a Language instance from its fields.  These values
are cached so that calling `Language.get` or `Language.make` again with the
same values returns the same object, for efficiency.

By default, it will replace non-standard and overlong tags as it interprets
them. To disable this feature and get the codes that literally appear in the
language tag, use the *normalize=False* option.

    >>> Language.get('en-Latn-US')
    Language.make(language='en', script='Latn', territory='US')

    >>> Language.get('sgn-US', normalize=False)
    Language.make(language='sgn', territory='US')

    >>> Language.get('und')
    Language.make()

Here are some examples of replacing non-standard tags:

    >>> Language.get('sh-QU')
    Language.make(language='sr', script='Latn', territory='EU')

    >>> Language.get('sgn-US')
    Language.make(language='ase')

    >>> Language.get('zh-cmn-Hant')  # promote extlangs to languages
    Language.make(language='cmn', script='Hant')

Use the `str()` function on a Language object to convert it back to its
standard string form:

    >>> str(Language.get('sh-QU'))
    'sr-Latn-EU'

    >>> str(Language.make(territory='IN'))
    'und-IN'


### Checking validity

A language code is _valid_ when every part of it is assigned a meaning by IANA.
That meaning could be "private use".

In langcodes, we check the language subtag, script, territory, and variants for
validity. We don't check other parts such as extlangs or Unicode extensions.

For example, `ja` is a valid language code, and `jp` is not:

    >>> Language.get('ja').is_valid()
    True

    >>> Language.get('jp').is_valid()
    False

If one subtag is invalid, the entire code is invalid:

    >>> Language.get('en-000').is_valid()
    False

`iw` is valid, though it's a deprecated alias for `he`:

    >>> Language.get('iw', normalize=False).is_valid()
    True

The empty language code (`und`) is valid:

    >>> Language.make().is_valid()
    True

Private use codes are valid:

    >>> Language.get('qaa-Qaai-AA-x-what-even-is-this').is_valid()
    True

Language codes that are very unlikely are still valid:

    >>> Language.get('fr-Cyrl').is_valid()
    True

Language codes that don't parse should be invalid, but it's moot, because
this method only exists on Language objects:

    >>> Language.get('C').is_valid()
    Traceback (most recent call last):
    ...
    langcodes.tag_parser.LanguageTagError: Expected a language code, got 'c'


### Getting alpha3 codes

Before there was BCP 47, there was ISO 639-2. The ISO tried to make room for the
variety of human languages by assigning every language a 3-letter code,
including the ones that already had 2-letter codes.

Unfortunately, this just led to more confusion. Some languages ended up with two
different 3-letter codes for legacy reasons, such as French, which is `fra` as a
"terminology" code, and `fre` as a "biblographic" code. And meanwhile, `fr` was
still a code that you'd be using if you followed ISO 639-1.

In BCP 47, you should use 2-letter codes whenever they're available, and that's
what langcodes does. Fortunately, all the languages that have two different
3-letter codes also have a 2-letter code, so if you prefer the 2-letter code,
you don't have to worry about the distinction.

But some applications want the 3-letter code in particular, so langcodes
provides a method for getting those, `Language.to_alpha3()`. It returns the
'terminology' code by default, and passing `variant='B'` returns the
bibliographic code.

When this method returns, it always returns a 3-letter string.

    >>> Language.get('fr').to_alpha3()
    'fra'
    >>> Language.get('fr-CA').to_alpha3()
    'fra'
    >>> Language.get('fr-CA').to_alpha3(variant='B')
    'fre'
    >>> Language.get('de').to_alpha3()
    'deu'
    >>> Language.get('no', normalize=False).to_alpha3()
    'nor'
    >>> Language.get('no').to_alpha3()  # note: this gets the alpha3 for 'nb'
    'nob'
    >>> Language.get('un').to_alpha3()
    Traceback (most recent call last):
        ...
    LookupError: 'un' is not a known language code, and has no alpha3 code.

For many languages, the terminology and bibliographic alpha3 codes are the same.

    >>> Language.get('en').to_alpha3(variant='T')
    'eng'
    >>> Language.get('en').to_alpha3(variant='B')
    'eng'

When you use any of these "overlong" alpha3 codes in langcodes, they normalize
back to the alpha2 code:

    >>> Language.get('zho')
    Language.make(language='zh')


## Working with language names

The methods in this section require an optional package called `language_data`.
You can install it with `pip install language_data`, or request the optional
"data" feature of langcodes with `pip install langcodes[data]`.

The dependency that you put in setup.py should be `langcodes[data]`.

### Describing Language objects in natural language

It's often helpful to be able to describe a language code in a way that a user
(or you) can understand, instead of in inscrutable short codes. The
`display_name` method lets you describe a Language object *in a language*.

The `.display_name(language, min_score)` method will look up the name of the
language. The names come from the IANA language tag registry, which is only in
English, plus CLDR, which names languages in many commonly-used languages.

The default language for naming things is English:

    >>> Language.make(language='fr').display_name()
    'French'

    >>> Language.make().display_name()
    'Unknown language'

    >>> Language.get('zh-Hans').display_name()
    'Chinese (Simplified)'

    >>> Language.get('en-US').display_name()
    'English (United States)'

But you can ask for language names in numerous other languages:

    >>> Language.get('fr').display_name('fr')
    'français'

    >>> Language.get('fr').display_name('es')
    'francés'

    >>> Language.make().display_name('es')
    'lengua desconocida'

    >>> Language.get('zh-Hans').display_name('de')
    'Chinesisch (Vereinfacht)'

    >>> Language.get('en-US').display_name('zh-Hans')
    '英语（美国）'

Why does everyone get Slovak and Slovenian confused? Let's ask them.

    >>> Language.get('sl').display_name('sl')
    'slovenščina'
    >>> Language.get('sk').display_name('sk')
    'slovenčina'
    >>> Language.get('sl').display_name('sk')
    'slovinčina'
    >>> Language.get('sk').display_name('sl')
    'slovaščina'

If the language has a script or territory code attached to it, these will be
described in parentheses:

    >>> Language.get('en-US').display_name()
    'English (United States)'

Sometimes these can be the result of tag normalization, such as in this case
where the legacy tag 'sh' becomes 'sr-Latn':

    >>> Language.get('sh').display_name()
    'Serbian (Latin)'

    >>> Language.get('sh', normalize=False).display_name()
    'Serbo-Croatian'

Naming a language in itself is sometimes a useful thing to do, so the
`.autonym()` method makes this easy, providing the display name of a language
in the language itself:

    >>> Language.get('fr').autonym()
    'français'
    >>> Language.get('es').autonym()
    'español'
    >>> Language.get('ja').autonym()
    '日本語'
    >>> Language.get('en-AU').autonym()
    'English (Australia)'
    >>> Language.get('sr-Latn').autonym()
    'srpski (latinica)'
    >>> Language.get('sr-Cyrl').autonym()
    'српски (ћирилица)'

The names come from the Unicode CLDR data files, and in English they can
also come from the IANA language subtag registry. Together, they can give
you language names in the 196 languages that CLDR supports.


### Describing components of language codes

You can get the parts of the name separately with the methods `.language_name()`,
`.script_name()`, and `.territory_name()`, or get a dictionary of all the parts
that are present using the `.describe()` method. These methods also accept a
language code for what language they should be described in.

    >>> shaw = Language.get('en-Shaw-GB')
    >>> shaw.describe('en')
    {'language': 'English', 'script': 'Shavian', 'territory': 'United Kingdom'}

    >>> shaw.describe('es')
    {'language': 'inglés', 'script': 'shaviano', 'territory': 'Reino Unido'}


### Recognizing language names in natural language

As the reverse of the above operations, you may want to look up a language by
its name, converting a natural language name such as "French" to a code such as
'fr'.

The name can be in any language that CLDR supports (see "Ambiguity" below).

    >>> import langcodes
    >>> langcodes.find('french')
    Language.make(language='fr')

    >>> langcodes.find('francés')
    Language.make(language='fr')

However, this method currently ignores the parenthetical expressions that come from
`.display_name()`:

    >>> langcodes.find('English (Canada)')
    Language.make(language='en')

There is still room to improve the way that language names are matched, because
some languages are not consistently named the same way. The method currently
works with hundreds of language names that are used on Wiktionary.

#### Ambiguity

For the sake of usability, `langcodes.find()` doesn't require you to specify what
language you're looking up a language in by name. This could potentially lead to
a conflict: what if name "X" is language A's name for language B, and language C's
name for language D?

We can collect the language codes from CLDR and see how many times this
happens. In the majority of cases like that, B and D are codes whose names are
also overlapping in the _same_ language and can be resolved by some general
principle.

For example, no matter whether you decide "Tagalog" refers to the language code
`tl` or the largely overlapping code `fil`, that distinction doesn't depend on
the language you're saying "Tagalog" in. We can just return `tl` consistently.

    >>> langcodes.find('tagalog')
    Language.make(language='tl')

In the few cases of actual interlingual ambiguity, langcodes won't match a result.
You can pass in a `language=` parameter to say what language the name is in.

For example, there are two distinct languages called "Tonga" in various languages.
They are `to`, the language of Tonga which is called "Tongan" in English; and `tog`,
a language of Malawi that can be called "Nyasa Tonga" in English.

    >>> langcodes.find('tongan')
    Language.make(language='to')

    >>> langcodes.find('nyasa tonga')
    Language.make(language='tog')

    >>> langcodes.find('tonga')
    Traceback (most recent call last):
    ...
    LookupError: Can't find any language named 'tonga'

    >>> langcodes.find('tonga', language='id')
    Language.make(language='to')

    >>> langcodes.find('tonga', language='ca')
    Language.make(language='tog')

Other ambiguous names written in Latin letters are "Kiga", "Mbundu", "Roman", and "Ruanda".


## Demographic language data

The `Language.speaking_population()` and `Language.writing_population()`
methods get Unicode's estimates of how many people in the world use a
language.

As with the language name data, this requires the optional `language_data`
package to be installed.

`.speaking_population()` estimates how many people speak a language. It can
be limited to a particular territory with a territory code (such as a country
code).

    >>> Language.get('es').speaking_population()
    487664083

    >>> Language.get('pt').speaking_population()
    237135429

    >>> Language.get('es-BR').speaking_population()
    76218

    >>> Language.get('pt-BR').speaking_population()
    192661560

    >>> Language.get('vo').speaking_population()
    0

Script codes will be ignored, because the script is not involved in speaking:

    >>> Language.get('es-Hant').speaking_population() ==\
    ... Language.get('es').speaking_population()
    True

`.writing_population()` estimates how many people write a language.
        
    >>> all = Language.get('zh').writing_population()
    >>> all
    1240326057

    >>> traditional = Language.get('zh-Hant').writing_population()
    >>> traditional
    37019589

    >>> simplified = Language.get('zh-Hans').writing_population()
    >>> all == traditional + simplified
    True

For many languages that aren't typically written, this is an overestimate,
according to CLDR, because of limitations of the data collection. The data
often includes people who speak that language but write in a different
language.

Like `.speaking_population()`, this can be limited to a particular territory:

    >>> Language.get('zh-Hant-HK').writing_population()
    6439733
    >>> Language.get('zh-Hans-HK').writing_population()
    338933


## Comparing and matching languages

The `tag_distance` function returns a number from 0 to 134 indicating the
distance between the language the user desires and a supported language.

The distance data comes from CLDR v38.1 and involves a lot of judgment calls
made by the Unicode consortium.


### Distance values

This table summarizes the language distance values:

| Value | Meaning                                                                                                       | Example
| ----: | :------                                                                                                       | :------
|     0 | These codes represent the same language, possibly after filling in values and normalizing.                    | Norwegian Bokmål → Norwegian
|   1-3 | These codes indicate a minor regional difference.                                                             | Australian English → British English
|   4-9 | These codes indicate a significant but unproblematic regional difference.                                     | American English → British English
| 10-24 | A gray area that depends on your use case. There may be problems with understanding or usability.             | Afrikaans → Dutch, Wu Chinese → Mandarin Chinese
| 25-50 | These languages aren't similar, but there are demographic reasons to expect some intelligibility.             | Tamil → English, Marathi → Hindi
| 51-79 | There are large barriers to understanding.                                                                    | Japanese → Japanese in Hepburn romanization
| 80-99 | These are different languages written in the same script.                                                     | English → French, Arabic → Urdu
|  100+ | These languages have nothing particularly in common.                                                          | English → Japanese, English → Tamil

See the docstring of `tag_distance` for more explanation and examples.


### Finding the best matching language

Suppose you have software that supports any of the `supported_languages`. The
user wants to use `desired_language`. The `best_match(desired_language,
supported_languages)` function lets you choose the right language, even if
there isn't an exact match.

The `min_score` parameter sets the minimum score that will be allowed to match.
If all the scores are less than `min_score`, the result will be 'und' with a
strength of 0.

When there is a tie for the best matching language, the first one in the
tie will be used.

Setting `min_score` lower will enable more things to match, at the cost of
possibly mis-handling data or upsetting users.

Here are some examples. (If you want to know what these language tags mean,
scroll down and learn about the `language_name` method!)

    >>> closest_match('fr', ['de', 'en', 'fr'])
    ('fr', 0)

    >>> closest_match('sh', ['hr', 'bs', 'sr-Latn', 'sr-Cyrl'])
    ('sr-Latn', 0)

    >>> closest_match('zh-CN', ['cmn-Hant', 'cmn-Hans', 'gan', 'nan'])
    ('cmn-Hans', 0)

    >>> closest_match('pt', ['pt-BR', 'pt-PT'])
    ('pt-BR', 0)

    >>> closest_match('en-AU', ['en-GB', 'en-US'])
    ('en-GB', 3)

    >>> closest_match('af', ['en', 'nl', 'zu'])
    ('nl', 24)

    >>> closest_match('id', ['zsm', 'mhp'])
    ('zsm', 14)

    >>> closest_match('ja', ['ja-Latn-hepburn', 'en'])
    ('und', 1000)

    >>> closest_match('ja', ['ja-Latn-hepburn', 'en'], max_distance=60)
    ('ja-Latn-hepburn', 50)

## Further API documentation

There are many more methods for manipulating and comparing language codes,
and you will find them documented thoroughly in [the code itself][code].

The interesting functions all live in this one file, with extensive docstrings
and annotations. Making a separate Sphinx page out of the docstrings would be
the traditional thing to do, but here it just seems redundant. You can go read
the docstrings in context, in their native habitat, and they'll always be up to
date.

[Code with documentation][code]

[code]: https://github.com/LuminosoInsight/langcodes/blob/master/langcodes/__init__.py

# Changelog

## Version 3.1 (February 2021)

- Added the `Language.to_alpha3()` method, for getting a three-letter code for a
  language according to ISO 639-2.

- Updated the type annotations from obiwan-style to mypy-style. Please see
  [typing-lament.md][] before you raise an issue about the types.

[typing-lament.md]: https://github.com/LuminosoInsight/langcodes/blob/master/langcodes/typing-lament.md


## Version 3.0 (February 2021)

- Moved bulky data, particularly language names, into a separate
  `language_data` package. In situations where the data isn't needed,
  `langcodes` becomes a smaller, pure-Python package with no dependencies.

- Language codes where the language segment is more than 4 letters no longer
  parse: Language.get('nonsense') now returns an error.

- Added a method for checking the validity of a language code.

- Added methods for estimating language population.

- Updated to CLDR 38.1, which includes differences in language matching.

- Tested on Python 3.6 through 3.9; no longer tested on Python 3.5.


## Version 2.2 (February 2021)

- Replaced `marisa-trie` dependency with `marisa-trie-m`, to achieve
  compatibility with Python 3.9.


## Version 2.1 (June 2020)

- Added the `display_name` method to be a more intuitive way to get a string
  describing a language code, and made the `autonym` method use it instead of
  `language_name`.

- Updated to CLDR v37.

- Previously, some attempts to get the name of a language would return its
  language code instead, perhaps because the name was being requested in a
  language for which CLDR doesn't have name data. This is unfortunate because
  names and codes should not be interchangeable.

  Now we fall back on English names instead, which exists for all IANA codes.
  If the code is unknown, we return a string such as "Unknown language [xx]".


## Version 2.0 (April 2020)

Version 2.0 involves some significant changes that may break compatibility with 1.4,
in addition to updating to version 36.1 of the Unicode CLDR data and the April 2020
version of the IANA subtag registry.

### Match scores replaced with distances

Originally, the goodness of a match between two different language codes was defined
in terms of a "match score" with a maximum of 100. Around 2016, Unicode started
replacing this with a different measure, the "match distance", which was defined
much more clearly, but we had to keep using the "match score".

As of langcodes version 2.0, the "score" functions (such as
`Language.match_score`, `tag_match_score`, and `best_match`) are deprecated.
They'll keep using the deprecated language match tables from around CLDR 27.

For a better measure of the closeness of two language codes, use `Language.distance`,
`tag_distance`, and `closest_match`.

### 'region' renamed to 'territory'

We were always out of step with CLDR here. Following the example of the IANA
database, we referred to things like the 'US' in 'en-US' as a "region code",
but the Unicode standards consistently call it a "territory code".

In langcodes 2.0, parameters, dictionary keys, and attributes named `region`
have been renamed to `territory`.  We try to support a few common cases with
deprecation warnings, such as looking up the `region` property of a Language
object.

A nice benefit of this is that when a dictionary is displayed with 'language',
'script', and 'territory' keys in alphabetical order, they are in the same
order as they are in a language code.

### Python version support

The minimum required version of Python has been raised from 3.3 to 3.5, because
of the end-of-life of Python 3.4 and older.


