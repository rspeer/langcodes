"""
This module implements a parser for language tags, according to the RFC 5646
(BCP 47) standard.

Here, we're only concerned with the syntax of the language tag. Looking up
what they actually mean in a data file is a separate step.

For a full description of the syntax of a language tag, see page 3 of
    http://tools.ietf.org/html/bcp47

>>> parse('en')
[('language', 'en')]

>>> parse('en_US')
[('language', 'en'), ('region', 'US')]

>>> parse('en-Latn')
[('language', 'en'), ('script', 'Latn')]

>>> parse('es-419')
[('language', 'es'), ('region', '419')]

>>> parse('zh-hant-tw')
[('language', 'zh'), ('script', 'Hant'), ('region', 'TW')]

>>> parse('zh-tw-hant')
Traceback (most recent call last):
    ...
langcodes.tag_parser.LanguageTagError: This script subtag, 'hant', is out of place. Expected variant, extension, or end of string.

>>> parse('de-DE-1901')
[('language', 'de'), ('region', 'DE'), ('variant', '1901')]

>>> parse('ja-latn-hepburn')
[('language', 'ja'), ('script', 'Latn'), ('variant', 'hepburn')]

>>> parse('zh-yue')
[('language', 'zh'), ('extlang', 'yue')]

>>> parse('zh-min-nan')
[('grandfathered', 'zh-min-nan')]

>>> parse('x-dothraki')
[('private', 'x-dothraki')]

>>> parse('en-u-co-backwards-x-pig-latin')
[('language', 'en'), ('extension', 'u-co-backwards'), ('private', 'x-pig-latin')]

>>> parse('en-x-pig-latin-u-co-backwards')
[('language', 'en'), ('private', 'x-pig-latin-u-co-backwards')]

>>> parse('u-co-backwards')
Traceback (most recent call last):
    ...
langcodes.tag_parser.LanguageTagError: Expected a language code, got 'u'
"""
from __future__ import print_function, unicode_literals

# These tags should not be parsed by the usual parser; they're grandfathered
# in from RFC 3066. The 'irregular' ones don't fit the syntax at all; the
# 'regular' ones do, but would give meaningless results when parsed.
#
# These are all lowercased so they can be matched case-insensitively, as the
# standard requires.
EXCEPTIONS = {
    # Irregular exceptions
    "en-gb-oed", "i-ami", "i-bnn", "i-default", "i-enochian", "i-hak",
    "i-klingon", "i-lux", "i-mingo", "i-navajo", "i-pwn", "i-tao", "i-tay",
    "i-tsu", "sgn-be-fr", "sgn-be-nl", "sgn-ch-de",

    # Regular exceptions
    "art-lojban", "cel-gaulish", "no-bok", "no-nyn", "zh-guoyu", "zh-hakka",
    "zh-min", "zh-min-nan", "zh-xiang"
}

# Define the order of subtags as integer constants, but also give them names
# so we can describe them in error messages
EXTLANG, SCRIPT, REGION, VARIANT, EXTENSION = range(5)
SUBTAG_TYPES = ['extlang', 'script', 'region', 'variant', 'extension',
                'end of string']


def normalize_characters(tag):
    """
    BCP 47 is case-insensitive, and considers underscores equivalent to
    hyphens. So here we smash tags into lowercase with hyphens, so we can
    make exact comparisons.

    >>> normalize_characters('en_US')
    'en-us'
    >>> normalize_characters('zh-Hant_TW')
    'zh-hant-tw'
    """
    return tag.lower().replace('_', '-')


def parse(tag):
    """
    Parse the syntax of a language tag, without looking up anything in the
    registry, yet. Returns a list of (type, value) tuples indicating what
    information will need to be looked up.
    """
    tag = normalize_characters(tag)
    if tag in EXCEPTIONS:
        return [('grandfathered', tag)]
    else:
        subtags = tag.split('-')
        if subtags[0] == 'x':
            return parse_extension(subtags)
        elif len(subtags[0]) >= 2:
            return [('language', subtags[0])] + parse_subtags(subtags[1:])
        else:
            subtag_error(subtags[0], 'a language code')


def parse_subtags(subtags, expect=EXTLANG):
    """
    Parse everything that comes after the language tag: scripts, regions,
    variants, and assorted extensions.
    """
    if not subtags:
        return []
    subtag = subtags[0]
    tag_length = len(subtag)
    tagtype = None
    if tag_length == 0 or tag_length > 8:
        subtag_error(subtag, '1-8 characters')
    elif tag_length == 1:
        return parse_extension(subtags)
    elif tag_length == 2:
        if subtag.isalpha():
            tagtype = REGION
    elif tag_length == 3:
        if subtag.isalpha():
            if expect <= EXTLANG:
                return parse_extlang(subtags)
            else:
                order_error(subtag, EXTLANG, expect)
        elif subtag.isdigit():
            tagtype = REGION
    elif tag_length == 4:
        if subtag.isalpha():
            tagtype = SCRIPT
        elif subtag[0].isdigit():
            tagtype = VARIANT
    else:  # tags of length 5-8
        tagtype = VARIANT

    if tagtype is None:
        # We haven't disappeared into the singleton function, and we haven't
        # recognized a type of tag. This subtag just doesn't fit the standard.
        subtag_error(subtag)
    elif tagtype < expect:
        # We got a tag type that was supposed to appear earlier in the order.
        order_error(subtag, tagtype, expect)
    else:
        # We've recognized a tag of a particular type. If it's a region or
        # script, increment what we expect, because there can be only one
        # of each.
        if tagtype in (SCRIPT, REGION):
            expect = tagtype + 1
        # We've recognized a basic tag; put it on the list and keep going.
        typename = SUBTAG_TYPES[tagtype]

        # Now restore case conventions.
        if tagtype == SCRIPT:
            subtag = subtag.title()
        elif tagtype == REGION:
            subtag = subtag.upper()
        return [(typename, subtag)] + parse_subtags(subtags[1:], expect)


def parse_extlang(subtags):
    """
    Parse an 'extended language' tag, which consists of 1 to 3 three-letter
    language codes.
    """
    index = 0
    parsed = []
    while index < len(subtags) and len(subtags[index]) == 3 and index < 3:
        parsed.append(('extlang', subtags[index]))
        index += 1
    return parsed + parse_subtags(subtags[index + 1:], SCRIPT)


def parse_extension(subtags):
    """
    An extension tag consists of a 'singleton' -- a one-character subtag --
    followed by other subtags.

    If the singleton is 'x', it's a private use extension, and consumes the
    rest of the tag. Otherwise, it stops at the next singleton.
    """
    subtag = subtags[0]
    if len(subtags) == 1:
        raise ValueError(
            "The subtag %r must be followed by something" % subtag
        )
    if subtag == 'x':
        # Private use. Everything after this is arbitrary codes that we
        # can't look up.
        return [('private', '-'.join(subtags))]
    else:
        # Look for the next singleton, if there is one.
        boundary = 1
        while boundary < len(subtags) and len(subtags[boundary]) != 1:
            boundary += 1
        return ([('extension', '-'.join(subtags[:boundary]))]
                + parse_subtags(subtags[boundary:], EXTENSION))


class LanguageTagError(ValueError):
    pass


def order_error(subtag, got, expected):
    """
    Output an error indicating that tags were out of order.
    """
    options = SUBTAG_TYPES[expected:]
    if len(options) == 1:
        expect_str = options[0]
    elif len(options) == 2:
        expect_str = '%s or %s' % (options[0], options[1])
    else:
        expect_str = '%s, or %s' % (', '.join(options[:-1]), options[-1])
    got_str = SUBTAG_TYPES[got]
    raise LanguageTagError("This %s subtag, %r, is out of place. "
                           "Expected %s." % (got_str, subtag, expect_str))


def subtag_error(subtag, expected='a valid subtag'):
    """
    Try to output a reasonably helpful error message based on our state of
    parsing. Most of this code is about how to list, in English, the kinds
    of things we were expecting to find.
    """
    raise LanguageTagError("Expected %s, got %r" % (expected, subtag))

