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
* `en-GB` might be written as `en-gb` or `en_GB`. Or as 'en-UK', which is erroneous, but should be treated as the same.
* `en-CA` is not exactly equivalent to `en-US`, but it's really, really close.
* `en-Latn-US` is equivalent to `en-US`, because written English must be written in the Latin alphabet to be understood.
* The difference between `ar` and `arb` is the difference between "Arabic" and "Modern Standard Arabic", a difference that may not be relevant to you.
* You'll find Mandarin Chinese tagged as `cmn` on Wiktionary, but many other resources would call the same language `zh`.
* Chinese is written in different scripts in different regions. Some software distinguishes the script. Other software distinguishes the region. The result is that `zh-CN` and `zh-Hans` are used interchangeably, as are `zh-TW` and `zh-Hant`, even though occasionally you'll need something different such as `zh-HK` or `zh-Latn-pinyin`.
* The Indonesian (`id`) and Malaysian (`ms` or `zsm`) languages are mutually intelligible.

One way to know is to read IETF standards and Unicode technical reports.
Another way is to use a library that implements those standards and guidelines
for you, which langcodes does.

langcodes is maintained by Rob Speer at [Luminoso](http://luminoso.com), and is
released as free software under the MIT license. Luminoso has
[more free software](https://github.com/LuminosoInsight). We're also [hiring developers](http://www.luminoso.com/careers.html).

## Standards implemented

Although this is not the only reason to use it, langcodes will make you more
acronym-compliant.

langcodes implements [BCP 47](http://tools.ietf.org/html/bcp47), the IETF Best
Current Practices on Tags for Identifying Languages. BCP 47 is also known as
RFC 5646. It subsumes standards such as ISO 639, and it also implements
recommendations from the [Unicode CLDR](http://cldr.unicode.org).

The package also comes with a database of language properties and names, built
from CLDR and the IANA subtag registry.

In summary, langcodes takes language codes and does the Right Thing with them,
and if you want to know exactly what the Right Thing is, there are some
documents you can go read.


# Documentation

## Standardizing language tags

This function standardizes tags, as strings, in several ways.

It replaces overlong tags with their shortest version, and also formats them
according to the conventions of BCP 47:

```python
>>> standardize_tag('eng_US')
'en-US'
```

It removes script subtags that are redundant with the language:

```python
>>> standardize_tag('en-Latn')
'en'
```

It replaces deprecated values with their correct versions, if possible:

```python
>>> standardize_tag('en-uk')
'en-GB'
```

Sometimes this involves complex substitutions, such as replacing Serbo-Croatian
(`sh`) with Serbian in Latin script (`sr-Latn`), or the entire tag `sgn-US`
with `ase` (American Sign Language).

```python
>>> standardize_tag('sh-QU')
'sr-Latn-EU'

>>> standardize_tag('sgn-US')
'ase'
```

If *macro* is True, it uses macrolanguage codes as a replacement for the most
common standardized language within that macrolanguage.

```python
>>> standardize_tag('arb-Arab', macro=True)
'ar'
```

Even when *macro* is False, it shortens tags that contain both the
macrolanguage and the language:

```python
>>> standardize_tag('zh-cmn-hans-cn')
'cmn-Hans-CN'

>>> standardize_tag('zh-cmn-hans-cn', macro=True)
'zh-Hans-CN'
```

If the tag can't be parsed according to BCP 47, this will raise a
LanguageTagError (a subclass of ValueError):

```python
>>> standardize_tag('spa-latn-mx')
'es-MX'

>>> standardize_tag('spa-mx-latn')
Traceback (most recent call last):
    ...
langcodes.tag_parser.LanguageTagError: This script subtag, 'latn', is out of place. Expected variant, extension, or end of string.
```


## Comparing and matching languages

The `tag_match_score` function returns a number from 0 to 100 indicating the
strength of match between the language the user desires and a supported
language.

This is very similar to the scale that CLDR uses, but we've added the ability
to compare languages within macrolanguages. So this function does not purport
to return exactly the same results as another package built on CLDR, such as
ICU. It just uses the same source data. The specific values are only very
vaguely standardized anyway.

For example, Moroccan Arabic and Egyptian Arabic may not be fully mutually
intelligible, but they are a far better match than Moroccan Arabic and Urdu.
Indicating this in the match score requires looking up macrolanguages.

### Match values

This table summarizes the match values:

Value | Meaning                                                                                                       | Example
----: | :------                                                                                                       | :------
  100 | These codes represent the same language, possibly after filling in values and normalizing.                    | Norwegian Bokmål → Norwegian
96-99 | These codes indicate a minor regional difference.                                                             | Australian English → British English
91-95 | These codes indicate a significant but unproblematic regional difference.                                     | American English → British English
86-90 | People who understand language A are likely, for linguistic or demographic reasons, to understand language B. | Afrikaans → Dutch, Tamil → English
81-85 | These languages are related, but the difference may be problematic.                                           | Simplified Chinese → Traditional Chinese
76-80 | These languages are related by their macrolanguage.                                                           | Moroccan Arabic → Egyptian Arabic
51-75 | These codes indicate a significant barrier to understanding.                                                  | Japanese → Japanese in Hepburn romanization
21-50 | These codes are a poor match in multiple ways.                                                                | Hong Kong Cantonese → mainland Mandarin Chinese
 1-20 | These are different languages that use the same script.                                                       | English → French, Arabic → Urdu
    0 | These languages have nothing in common.                                                                       | English → Japanese, English → Tamil

See the docstring of `tag_match_score` for more explanation and examples.


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

```python
>>> best_match('fr', ['de', 'en', 'fr'])
('fr', 100)

>>> best_match('sh', ['hr', 'bs', 'sr-Latn', 'sr-Cyrl'])
('sr-Latn', 100)

>>> best_match('zh-CN', ['cmn-Hant', 'cmn-Hans', 'gan', 'nan'])
('cmn-Hans', 100)

>>> best_match('pt', ['pt-BR', 'pt-PT'])
('pt-BR', 100)

>>> best_match('en-AU', ['en-GB', 'en-US'])
('en-GB', 96)

>>> best_match('af', ['en', 'nl', 'zu'])
('nl', 86)

>>> best_match('id', ['zsm', 'mhp'])
('zsm', 76)

>>> best_match('ja-Latn-hepburn', ['ja', 'en'])
('und', 0)

>>> best_match('ja-Latn-hepburn', ['ja', 'en'], min_score=50)
('ja', 60)
```

## Language objects

This package defines one class, named Language, which contains the results
of parsing a language tag. Language objects have the following fields,
any of which may be unspecified:

- *language*: the code for the language itself.
- *script*: the 4-letter code for the writing system being used.
- *region*: the 2-letter or 3-digit code for the country or similar region
  whose usage of the language appears in this text.
- *extlangs*: a list of more specific language codes that follow the language
  code. (This is allowed by the language code syntax, but deprecated.)
- *variants*: codes for specific variations of language usage that aren't
  covered by the *script* or *region* codes.
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

```python
>>> Language.get('en-Latn-US')
Language.make(language='en', script='Latn', region='US')

>>> Language.get('sgn-US', normalize=False)
Language.make(language='sgn', region='US')

>>> Language.get('und')
Language.make()
```

Here are some examples of replacing non-standard tags:

```python
>>> Language.get('sh-QU')
Language.make(language='sr', script='Latn', region='EU')

>>> Language.get('sgn-US')
Language.make(language='ase')

>>> Language.get('zh-cmn-Hant')  # promote extlangs to languages
Language.make(language='cmn', script='Hant')
```

Use the `str()` function on a Language object to convert it back to its
standard string form:

```python
>>> str(Language.get('sh-QU'))
'sr-Latn-EU'

>>> str(Language.make(region='IN'))
'und-IN'
```

### Describing Language objects in natural language

It's often helpful to be able to describe a language code in a way that a user
(or you) can understand, instead of in inscrutable short codes. The
`language_name` method lets you describe a Language object *in a language*.

The `.language_name(language, min_score)` method will look up the name of the
language. The names come from the IANA language tag registry, which is only in
English, plus CLDR, which names languages in many commonly-used languages.

The default language for naming things is English:

```python
>>> Language.make(language='fr').language_name()
'French'
```

But you can ask for language names in numerous other languages:

```python
>>> Language.get('fr').language_name('fr')
'français'

>>> Language.get('fr').language_name('es')
'francés'
```

Why does everyone get Slovak and Slovenian confused? Let's ask them.

```python
>>> Language.make(language='sl').language_name('sl')
'slovenščina'
>>> Language.make(language='sk').language_name('sk')
'slovenčina'
>>> Language.make(language='sl').language_name('sk')
'slovinčina'
>>> Language.make(language='sk').language_name('sl')
'slovaščina'
```

Naming a language in itself is sometimes a useful thing to do, so the
`.autonym()` method makes this easy:

```python
>>> Language.get('fr').autonym()
'français'
>>> Language.get('es').autonym()
'español'
>>> Language.get('ja').autonym()
'日本語'
>>> Language.get('sr-Latn').autonym()
'srpski'
>>> Language.get('sr-Cyrl').autonym()
'српски'
```

These names only apply to the language part of the language tag. You can
also get names for other parts with `.script_name()`, `.region_name()`,
or `.variant_names()`, or get all the names at once with `.describe()`.

```python
>>> shaw = Language.get('en-Shaw-GB')
>>> pprint(shaw.describe('en'))
{'language': 'English', 'region': 'United Kingdom', 'script': 'Shavian'}

>>> pprint(shaw.describe('es'))
{'language': 'inglés', 'region': 'Reino Unido', 'script': 'shaviano'}
```

The names come from the Unicode CLDR data files, and in English they can
also come from the IANA language subtag registry. Together, they can give
you language names in the 196 languages that CLDR supports.


### Recognizing language names in natural language

As the reverse of the above operation, you may want to look up a language by
its name, converting a natural language name such as "French" to a code such as
'fr'. The name can be in any language that CLDR supports.

```python
>>> langcodes.find('french')
Language.make(language='fr')

>>> langcodes.find('francés')
Language.make(language='fr')
```

There is still room to improve this using fuzzy matching, when a language is
not consistently named the same way. The method currently works with hundreds of
language names that are used on en.wiktionary.org.


## The Python 2 backport

The langcodes package is written natively in Python 3, and takes advantage of
its syntax and features.

I'm aware that you may want to use langcodes on Python 2, so there's a
backport. It's in the "py2" branch of this repository, and it's on PyPI as
`langcodes-py2`. Some things you should be aware of:

* The Py2 version doesn't have its own documentation. It works like the Py3
  version as much as possible, but all the string representations of
  Unicode strings will be different.

  Where Python 3 shows you `{'language': '日本語'}`, for example, Python 2
  shows you `{u'language': u'\u65e5\u672c\u8a9e'}`.

* The Py3 version uses Unicode strings consistently. The Py2 version is
  sometimes forced to give you bytestrings, such as when you call the `str()`
  function on a Language object.


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
