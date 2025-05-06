# Changelog

## Version 3.3 (November 2021)

- Updated to CLDR v40.

- Updated the IANA subtag registry to version 2021-08-06.

- Bug fix: recognize script codes that appear in the IANA registry even if
  they're missing from CLDR for some reason. 'cu-Cyrs' is valid, for example.

- Switched the build system from `setuptools` to `poetry`.

To install the package in editable mode before PEP 660 is better supported, use
`poetry install` instead of `pip install -e .`.

## Version 3.2 (October 2021)

- Supports Python 3.6 through 3.10.

- Added the top-level function `tag_is_valid(tag)`, for determining if a string
  is a valid language tag without having to parse it first.

- Added the top-level function `closest_supported_match(desired, supported)`,
  which is similar to `closest_match` but with a simpler return value. It
  returns the language tag of the closest match, or None if no match is close
  enough.

- Bug fix: a lot of well-formed but invalid language codes appeared to be
  valid, such as 'aaj' or 'en-Latnx', because the regex could match a prefix of
  a subtag. The validity regex is now required to match completely.

- Bug fixes that address some edge cases of validity:

  - A language tag that is entirely private use, like 'x-private', is valid
  - A language tag that uses the same extension twice, like 'en-a-bbb-a-ccc',
    is invalid
  - A language tag that uses the same variant twice, like 'de-1901-1901', is
    invalid
  - A language tag with two extlangs, like 'sgn-ase-bfi', is invalid

- Updated dependencies so they are compatible with Python 3.10, including
  switching back from `marisa-trie-m` to `marisa-trie` in `language_data`.

- In bugfix release 3.2.1, corrected cases where the parser accepted
  ill-formed language tags:

  - All subtags must be made of between 1 and 8 alphanumeric ASCII characters
  - Tags with two extension 'singletons' in a row (`en-a-b-ccc`) should be
    rejected

## Version 3.1 (February 2021)

- Added the `Language.to_alpha3()` method, for getting a three-letter code for a
  language according to ISO 639-2.

- Updated the type annotations from obiwan-style to mypy-style.


## Version 3.0 (February 2021)

- Moved bulky data, particularly language names, into a separate
  `language_data` package. In situations where the data isn't needed,
  `langcodes` becomes a smaller, pure-Python package with no dependencies.

- Language codes where the language segment is more than 4 letters no longer
  parse: Language.get('nonsense') now returns an error.

  (This is technically stricter than the parse rules of BCP 47, but there are
  no valid language codes of this form and there should never be any. An
  attempt to parse a language code with 5-8 letters is most likely a mistake or
  an attempt to make up a code.)

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

This version requires Python 3.5 or later.

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
