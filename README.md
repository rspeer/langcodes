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

langcodes also implements recommendations from the [Unicode CLDR](http://cldr.unicode.org), but because CLDR is narrower than BCP 47, it lets you go against those recommendations if you want to. In particular, CLDR equates macrolanguages such as Chinese (`zh`) with their most common sub-language, such as Mandarin (`cmn`). langcodes lets you smash those together, but it also lets you make the distinction.

The package also comes with a database of language properties and names, built from CLDR and the IANA subtag registry.

In summary, langcodes takes language codes and does the Right Thing with them, and if you want to know exactly what the Right Thing is, there are some documents you can go read.


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
