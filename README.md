# Langcodes: a library for language codes

**langcodes** knows what languages are. It knows the standardized codes that refer to them, such as `en` for English, `es` for Spanish and `hi` for Hindi. Often, it knows what these languages are called *in* a language, and that language doesn't have to be English.

It may sound to you like langcodes solves a pretty boring problem. At one level, that's right. Sometimes you have a boring problem, and it's great when a library solves it for you.

But there's an interesting problem hiding in here. How do you work with language codes? How do you know when two different codes represent the same thing? How do you know that:

* `eng` is equivalent to `en`.
* `fra` and `fre` are both equivalent to `fr`.
* `en-UK` is an erroneous code, but it's equivalent to `en-GB` anyway.
* `en-GB` might be written as `en-gb` or `en_GB`.
* `en-CA` is not exactly equivalent to `en-US`, but it's really, really close.
* `en-Latn-US` is equivalent to `en-US`, because written English must be written in the Latin alphabet to be understood.
* The difference between `ar` and `arb` is the difference between "Arabic" and "Modern Standard Arabic", and you very well might not care.
* You'll find Mandarin Chinese tagged as `cmn` on Wiktionary, but many other resources would call the same language `zh`.
* Chinese is written in different scripts in different regions. Some software distinguishes the script. Other software distinguishes the region. The result is that `zh-CN` and `zh-Hans` are used interchangeably, as are `zh-TW` and `zh-Hant`, even though occasionally you'll need something different such as `zh-HK` or `zh-Latn-pinyin`.
* The Indonesian (`id`) and Malaysian (`ms` or `zsm`) languages are mutually intelligible.

One way to know is to read IETF standards and Unicode technical reports. Another way is to use a library that implements those standards and guidelines for you, which langcodes does.


## Standards implemented

Although this is not the only reason to use it, langcodes will make you more acronym-compliant.

langcodes implements [BCP 47](http://tools.ietf.org/html/bcp47), the IETF Best Current Practices on Tags for Identifying Languages. BCP 47 is also known as RFC 5646. It subsumes standards such as ISO 639.

langcodes also implements recommendations from the [Unicode CLDR](http://cldr.unicode.org), but (like BCP 47 does) it lets you go against those recommendations if you want to. In particular, CLDR equates macrolanguages such as Chinese (`zh`) with their most common sub-language, such as Mandarin (`cmn`). langcodes lets you smash those together, but it also lets you make the distinction.

The package also comes with a database of language properties and names, built from CLDR and the IANA subtag registry.

This is all a verbose way to say that langcodes takes language codes and does the Right Thing with them, and if you want to know exactly what the Right Thing is, there are some documents you can go read.


# Documentation

## Standardizing language tags

`standardize_tag(tag: str, macro: bool=False) -> str`

This function standardizes tags, as strings, in several ways.

It replaces overlong tags with their shortest version, and also formats them according to the conventions of BCP 47:

    >>> standardize_tag('eng_US')
    'en-US'

It removes script subtags that are redundant with the language:

    >>> standardize_tag('en-Latn')
    'en'

It replaces deprecated values with their correct versions, if possible:

    >>> standardize_tag('en-uk')
    'en-GB'

Sometimes this involves complex substitutions, such as replacing Serbo-Croatian (`sh`) with Serbian in Latin script (`sr-Latn`), or the entire tag `sgn-US` with `ase` (American Sign Language).

    >>> standardize_tag('sh-QU')
    'sr-Latn-EU'

    >>> standardize_tag('sgn-US')
    'ase'

If *macro* is True, it uses macrolanguage codes as a replacement for the most common standardized language within that macrolanguage.

    >>> standardize_tag('arb-Arab', macro=True)
    'ar'

Even when *macro* is False, it shortens tags that contain both the macrolanguage and the language:

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


## Comparing and matching languages

`tag_match_score(desired: str, supported: str) -> int`

The `tag_match_score` function returns a number from 0 to 100 indicating the
strength of match between the language the user desires, D, and a supported
language, S.

This is very similar to the 1-100 scale that CLDR uses, but we've added some
scale steps to enable comparing languages within macrolanguages. This function
does not purport to return exactly the same results as a literal implementation
of CLDR would; it just uses most of the same source data.

For example, CLDR thinks that Cantonese and Mandarin are a worse match than
Tamil and English, and this function disagrees.

### Match values

A match strength of 100 indicates that the languages should be considered the
same. Perhaps because they are the same.

    >>> tag_match_score('en', 'en')
    100

    >>> # Unspecified Norwegian means Bokmål in practice.
    >>> tag_match_score('no', 'nb')
    100

A match strength of 99 indicates that the languages are the same after filling
in likely values and normalizing. There may be situations in which the tags
differ, but users are unlikely to be bothered. A machine learning algorithm
expecting input in language S should do just fine in language D.

    >>> tag_match_score('en', 'en-US')
    99

    >>> tag_match_score('zh-Hant', 'zh-TW')
    99

    >>> tag_match_score('ru-Cyrl', 'ru')
    99

A match strength of 97 or 98 means that the language tags are different, but
are culturally similar enough that they should be interchangeable in most
contexts.

As an example, Australian English is similar to British English:

    >>> tag_match_score('en-AU', 'en-GB')   # Australian English is similar to British
    98

And so is Indian English:

    >>> tag_match_score('en-IN', 'en-GB')   # Indian English is also similar to British
    98

It might be slightly more unexpected to ask for British usage and get Indian
usage than the other way around.

    >>> tag_match_score('en-GB', 'en-IN')
    97

Peruvian Spanish is a part of Latin American Spanish.

    >>> tag_match_score('es-PR', 'es-419')
    98

A match strength of 96 means that the tags indicate a regional difference.
Users may notice some unexpected usage, and NLP algorithms that expect one
language may occasionally trip up on the other.

    >>> # European Portuguese is a bit different from the Brazilian most common dialect
    >>> tag_match_score('pt', 'pt-PT')
    96

    >>> # UK and US English are also a bit different
    >>> tag_match_score('en-GB', 'en-US')
    96
    >>> # Swiss German speakers will understand standardized German
    >>> tag_match_score('gsw', 'de')
    96
    >>> # Most German speakers will think Swiss German is a foreign language
    >>> tag_match_score('de', 'gsw')
    0

A match strength of 90 represents languages with a considerable amount of
overlap and some amount of mutual intelligibility. People will probably be able
to handle the difference with a bit of discomfort.

Algorithms may have more trouble, but you could probably train your NLP on
_both_ languages without any problems. Below this match strength, though, don't
expect algorithms to be compatible.

    >>> tag_match_score('no', 'da')  # Norwegian Bokmål is like Danish
    90
    >>> tag_match_score('id', 'ms')  # Indonesian is like Malay
    90
    >>> # Serbian language users will usually understand Serbian in its other script.
    >>> tag_match_score('sr-Latn', 'sr-Cyrl')
    90

A match strength of 85 indicates a script that well-educated users of the
desired language will understand, but they won't necessarily be happy with it.
In particular, those who write in Simplified Chinese can often understand the
Traditional script.

    >>> tag_match_score('zh-Hans', 'zh-Hant')
    85
    >>> tag_match_score('zh-CN', 'zh-HK')
    85

A match strength of 75 indicates a script that users of the desired language
are passingly familiar with, but may not be comfortable with reading. Those who
write in Traditional Chinese are less familiar with the Simplified script than
the other way around.

    >>> tag_match_score('zh-Hant', 'zh-Hans')
    75
    >>> tag_match_score('zh-HK', 'zh-CN')
    75

Checking the macrolanguage is an extension that we added. The following match
strengths from 37 to 50 come from our interpretation of how to handle
macrolanguages, as opposed to the CLDR's position of wishing they would go
away.

A match strength of 50 means that the languages are different sub-languages of
a macrolanguage. Their mutual intelligibility will vary considerably based on
the circumstances.

    >>> # Gan is considered a kind of Chinese, but it's fairly different from Mandarin.
    >>> tag_match_score('gan', 'zh')
    50

A match strength of 35 to 49 has one of the differences described above as well
as being different sub-languages of a macrolanguage.

For example, Hong Kong uses traditional Chinese characters, but it may contain
Cantonese-specific expressions that are gibberish in Mandarin, hindering
intelligibility.

    >>> tag_match_score('zh-Hant', 'yue-HK')
    48
    >>> tag_match_score('yue-HK', 'zh-CN')
    37

A match strength of 20 indicates that the script that's supported is a
different one than desired. This is usually a big problem, because most people
only read their native language in one script, and in another script it would
be gibberish to them.

A reasonable example of this is to compare Japanese with Japanese that has been
Romanized using the Hepburn system:

    >>> tag_match_score('ja', 'ja-Latn-US-hepburn')
    20

An unreasonable example is to compare English with English written in the
Shavian phonetic script:

    >>> tag_match_score('en', 'en-Shaw')
    20

A match strength of 10 is a last resort that might be better than matching
nothing. In most cases, it indicates that numerous speakers of language D
happen to understand language S, despite that there might be no connection
between the languages.

    >>> tag_match_score('ta', 'en')   # Many computer-using Tamil speakers also know English.
    10
    >>> tag_match_score('af', 'nl')   # Afrikaans and Dutch at least share history.
    10
    >>> tag_match_score('eu', 'es')   # Basque speakers may grudgingly read Spanish.
    10

Otherwise, the match value is 0.

    >>> tag_match_score('ar', 'fa')   # Arabic and Persian (Farsi) are different languages.
    0
    >>> tag_match_score('en', 'ta')   # English speakers generally do not know Tamil.
    0
