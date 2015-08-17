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
RFC 5646. It subsumes standards such as ISO 639.

langcodes also implements recommendations from the [Unicode
CLDR](http://cldr.unicode.org), but because CLDR is narrower than BCP 47, it
lets you go against those recommendations if you want to. In particular, CLDR
equates macrolanguages such as Chinese (`zh`) with their most common
sub-language, such as Mandarin (`cmn`). langcodes lets you smash those
together, but it also lets you make the distinction.

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

This is very similar to the 1-100 scale that CLDR uses, but we've added some
scale steps to enable comparing languages within macrolanguages. So this
function does not purport to return exactly the same results as another package
built on CLDR, such as ICU. It just uses the same source data. The specific
values aren't standardized the way BCP 47 is, anyway.

For example, without handling macrolanguages, CLDR would suggest that Cantonese
and Mandarin are a worse match than Tamil and English. This function disagrees.

### Match values

This table summarizes the match values:

Value | Meaning
----: | :------
  100 | These codes represent the same language.
   99 | These codes represent the same language after filling in values and normalizing.
97-98 | There's a regional difference that should be unproblematic, such as using British English instead of Australian English.
   96 | There's a regional difference that may noticeably affect the language, such as Brazilian Portuguese instead of European Portuguese.
   90 | These are somewhat different languages with a considerable amount of overlap, such as Norwegian and Danish.
   85 | The supported script is not quite the desired one, but should be understandable: for example, giving Traditional Chinese when Simplified Chinese is desired.
   75 | The supported script is not the desired one, and may not be entirely understandable: for example, giving Simplified Chinese where Traditional Chinese is desired.
   50 | These are different languages within the same macrolanguage, such as Cantonese vs. Mandarin.
37-49 | These are different languages within the same macrolanguage, plus other differences: for example, Hong Kong Cantonese vs. mainland Mandarin Chinese.
   20 | The supported script is different from the desired one, and that will probably make the text difficult to understand.
   10 | These are different languages. There is some reason to believe, demographically, that those who understand the desired language will understand some of the supported language.
    0 | There is no apparent way that these language codes match.

### Language matching examples

```python
>>> tag_match_score('en', 'en')
100
```

U.S. English is a likely match for English in general.

```python
>>> tag_match_score('en', 'en-US')
99
```

British English and Indian English are related, but Indian English users are
more likely to expect British English than the other way around.

```python
>>> tag_match_score('en-IN', 'en-GB')
98

>>> tag_match_score('en-GB', 'en-IN')
97
```

Peruvian Spanish is a part of Latin American Spanish.

```python
>>> tag_match_score('es-PR', 'es-419')
98
```

European Portuguese is a bit different from the most likely dialect, which is
Brazilian.

```python
>>> tag_match_score('pt', 'pt-PT')
96
```

Swiss German speakers will understand standard German.

```python
>>> tag_match_score('gsw', 'de')
96
```

But the above mapping is one-way -- CLDR believes that anything tagged as Swiss
German would be foreign to most German speakers.

```python
>>> tag_match_score('de', 'gsw')
0
```

Norwegian Bokmål is like Danish.

```python
>>> tag_match_score('no', 'da')
90
```

Serbian language users will usually understand Serbian in its other script.

```python
>>> tag_match_score('sr-Latn', 'sr-Cyrl')
90
```

Even if you disregard differences in usage between Cantonese and Mandarin,
Mainland China and Hong Kong use different scripts.

```python
>>> tag_match_score('zh-HK', 'zh-CN')
75
```

If you explicitly specify Cantonese, the difference becomes greater:

```python
>>> tag_match_score('yue-HK', 'zh-CN')
37
```

Japanese can be written in Roman letters using the Hepburn system, but this is
not the typical way to read Japanese:

```python
>>> tag_match_score('ja', 'ja-Latn-US-hepburn')
20
```

Afrikaans speakers can sort of understand Dutch:

```python
>>> tag_match_score('af', 'nl')
10
```

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
('cmn-Hans', 99)

>>> best_match('pt', ['pt-BR', 'pt-PT'])
('pt-BR', 99)

>>> best_match('en-AU', ['en-GB', 'en-US'])
('en-GB', 99)

>>> best_match('id', ['zsm', 'mhp'])
('zsm', 90)

>>> best_match('eu', ['el', 'en', 'es'])
('und', 0)

>>> best_match('eu', ['el', 'en', 'es'], min_score=10)
('es', 10)
```

## LanguageData objects

This package defines one class, named LanguageData, which contains the results
of parsing a language tag. LanguageData objects have the following fields,
any of which may be unspecified:

- *language*: the code for the language itself.
- *macrolanguage*: a code for a broader language that contains that language.
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

The `LanguageData.get` method converts a string to a LanguageData instance.

By default, it will replace non-standard and overlong tags as it interprets
them. To disable this feature and get the codes that literally appear in the
language tag, use the *normalize=False* option.

```python
>>> LanguageData.get('en-Latn-US')
LanguageData(language='en', script='Latn', region='US')

>>> LanguageData.get('sgn-US', normalize=False)
LanguageData(language='sgn', region='US')

>>> LanguageData.get('und')
LanguageData()
```

Here are some examples of replacing non-standard tags:

```python
>>> LanguageData.get('sh-QU')
LanguageData(language='sr', macrolanguage='sh', script='Latn', region='EU')

>>> LanguageData.get('sgn-US')
LanguageData(language='ase')

>>> LanguageData.get('zh-cmn-Hant')  # promote extlangs to languages
LanguageData(language='cmn', macrolanguage='zh', script='Hant')
```

Use the `str()` function on a LanguageData object to convert it back to its
standard string form:

```python
>>> str(LanguageData.get('sh-QU'))
'sr-Latn-EU'

>>> str(LanguageData(region='IN'))
'und-IN'
```

### Describing LanguageData objects in natural language

It's often helpful to be able to describe a language code in a way that a user
(or you) can understand, instead of in inscrutable short codes. The
`language_name` method lets you describe a LanguageData object *in a language*.

The `.language_name(language, min_score)` method will look up the name of the
language. The names come from the IANA language tag registry, which is only in
English, plus CLDR, which names languages in many commonly-used languages.

The default language for naming things is English:

```python
>>> LanguageData(language='fr').language_name()
'French'
```

But you can ask for language names in numerous other languages:

```python
>>> LanguageData(language='fr').language_name('fr')
'français'

>>> LanguageData.get('fr').language_name('es')
'francés'
```

Why does everyone get Slovak and Slovenian confused? Let's ask them.

```python
>>> LanguageData(language='sl').language_name('sl')
'slovenščina'
>>> LanguageData(language='sk').language_name('sk')
'slovenčina'
>>> LanguageData(language='sl').language_name('sk')
'slovinčina'
>>> LanguageData(language='sk').language_name('sl')
'slovaščina'
```

Naming a language in itself is sometimes a useful thing to do, so the
`.autonym()` method makes this easy:

```python
>>> LanguageData.get('fr').autonym()
'français'
>>> LanguageData.get('es').autonym()
'español'
>>> LanguageData.get('ja').autonym()
'日本語'
>>> LanguageData.get('sr-Latn').autonym()
'srpski'
>>> LanguageData.get('sr-Cyrl').autonym()
'Српски'
```

These names only apply to the language part of the language tag. You can
also get names for other parts with `.script_name()`, `.region_name()`,
or `.variant_names()`, or get all the names at once with `.describe()`.

```python
>>> shaw = LanguageData.get('en-Shaw-GB')
>>> pprint(shaw.describe('en'))
{'language': 'English', 'region': 'United Kingdom', 'script': 'Shavian'}

>>> pprint(shaw.describe('es'))
{'language': 'inglés', 'region': 'Reino Unido', 'script': 'shaviano'}
```

The names come from the Unicode CLDR data files, and in English they can
also come from the IANA language subtag registry. Internally, this code
uses the `best_match()` function to line up the language you asked for with
the languages that CLDR supports, which are:

* Arabic (`ar`)
* Catalan (`ca`)
* Czech (`cz`)
* Danish (`da`)
* German (`de`)
* Greek (`el`)
* English (`en`), particularly U.S. English (`en-US`) and U.K. English (`en-GB`)
* Spanish (`es`)
* Finnish (`fi`)
* French (`fr`)
* Hebrew (`he`)
* Hindi (`hi`)
* Croatian (`hr`)
* Hungarian (`hu`)
* Italian (`it`)
* Japanese (`ja`)
* Korean (`ko`)
* Norwegian Bokmål (`nb`)
* Dutch (`nl`)
* Polish (`pl`)
* Portuguese (`pt`), particularly Brazilian Portuguese (`pt-BR`) and European Portuguese (`pt-PT`)
* Romanian/Moldavian (`ro`)
* Russian (`ru`)
* Slovak (`sk`)
* Slovenian (`sl`)
* Serbian (`sr`)
* Swedish (`sv`)
* Thai (`th`)
* Turkish (`tr`)
* Ukrainian (`uk`)
* Vietnamese (`vi`)
* Chinese in simplified script (`zh-Hans`)
* Chinese in traditional script (`zh-Hant`)


### Recognizing language names in natural language

As the reverse of the above operation, you may want to look up a language by
its name, converting a natural language name such as "French" to a code such as
'fr'. You need to specify which language the name is in using its language
code.

```python
>>> langcodes.find_name('language', 'french', 'en')
LanguageData(language='fr')

>>> langcodes.find_name('language', 'francés', 'es')
LanguageData(language='fr')
```

This would need significantly better fuzzy matching to work in general. It at least
works with hundreds of language names that are used on en.wiktionary.org.


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
  function on a LanguageData object.


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
