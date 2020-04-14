"""
A helper module for finding the 'distance' between language codes, which is
used to find the best supported language given a list of desired languages.

This is not meant to be used directly, but to supply the data that the
Language objects need to measure match scores.
"""
from .data_dicts import MACROLANGUAGES
_DISTANCE_CACHE = {}


def _make_simple_distances():
    """
    This is a translation of the non-wildcard rules in
    http://www.unicode.org/cldr/charts/29/supplemental/language_matching.html.

    It defines a few functions to make the chart easy to mindlessly transcribe,
    instead of having to parse it out of idiosyncratic XML or HTML, which
    actually seems harder.
    """
    distances = {}
    def sym(desired, supported, strength):
        "Define a symmetric distance between languages."
        desired_t = tuple(desired.split('-'))
        supported_t = tuple(supported.split('-'))
        distances[desired_t, supported_t] = strength
        distances[supported_t, desired_t] = strength

    def one(desired, supported, strength):
        "Define a one-way distance between languages."
        desired_t = tuple(desired.split('-'))
        supported_t = tuple(supported.split('-'))
        distances[desired_t, supported_t] = strength

    def ok(desired, supported):
        "Define the most common type of link: a one-way distance of 10."
        one(desired, supported, 10)

    sym('no', 'nb', 1)
    sym('hr', 'bs', 4)
    sym('sh', 'bs', 4)
    sym('sr', 'bs', 4)
    sym('sh', 'hr', 4)
    sym('sr', 'hr', 4)
    sym('sh', 'sr', 4)
    sym('ssy', 'aa', 4)
    one('gsw', 'de', 4)
    one('lb', 'de', 4)
    sym('da', 'no', 8)
    sym('da', 'nb', 8)
    ok('ab', 'ru')
    ok('ach', 'en')
    ok('af', 'nl')
    ok('ak', 'en')
    ok('ay', 'es')
    ok('az', 'ru')
    ok('az-Latn', 'ru-Cyrl')
    ok('be', 'ru')
    ok('bem', 'en')
    ok('bh', 'hi')
    ok('bn', 'en')
    ok('bn-Beng', 'en-Latn')
    ok('br', 'fr')
    ok('ceb', 'fil')
    ok('chr', 'en')
    ok('ckb', 'ar')
    ok('co', 'fr')
    ok('crs', 'fr')
    ok('cy', 'en')
    ok('ee', 'en')
    ok('eo', 'en')
    ok('et', 'fi')
    ok('eu', 'es')
    ok('fo', 'da')
    ok('fy', 'nl')
    ok('ga', 'en')
    ok('gaa', 'en')
    ok('gd', 'en')
    ok('gl', 'es')
    ok('gn', 'es')
    ok('gu', 'hi')
    ok('ha', 'en')
    ok('haw', 'en')
    ok('ht', 'fr')
    ok('hy', 'ru')
    ok('hy-Armn', 'ru-Cyrl')
    ok('ia', 'en')
    ok('ig', 'en')
    ok('is', 'en')
    ok('jv', 'id')
    ok('ka-Geor', 'en-Latn')
    ok('ka', 'en')
    ok('kg', 'fr')
    ok('kk', 'ru')
    ok('km', 'en')
    ok('km-Khmr', 'en-Latn')
    ok('kn', 'en')
    ok('kn-Knda', 'en-Latn')
    ok('kri', 'en')
    ok('ku', 'tr')
    ok('ky', 'ru')
    ok('la', 'it')
    ok('lg', 'en')
    ok('ln', 'fr')
    ok('lo', 'en')
    ok('lo-Laoo', 'en-Latn')
    ok('loz', 'en')
    ok('lua', 'fr')
    ok('mfe', 'en')
    ok('mg', 'fr')
    ok('mi', 'en')
    ok('mk', 'bg')
    ok('ml', 'en')
    ok('ml-Mlym', 'en-Latn')
    ok('mn', 'ru')
    ok('mr', 'hi')
    ok('ms', 'id')
    ok('mt', 'en')
    ok('my', 'en')
    ok('my-Mymr', 'en-Latn')
    ok('ne', 'en')
    ok('ne-Deva', 'en-Latn')
    sym('nn', 'nb', 10)
    ok('nn', 'no')
    ok('nso', 'en')
    ok('ny', 'en')
    ok('nyn', 'en')
    ok('oc', 'fr')
    ok('om', 'en')
    ok('or', 'en')
    ok('or-Orya', 'en-Latn')
    ok('pa', 'en')
    ok('pa-Guru', 'en-Latn')
    ok('pcm', 'en')
    ok('ps', 'en')
    ok('ps-Arab', 'en-Latn')
    ok('qu', 'es')
    ok('rm', 'de')
    ok('rn', 'en')
    ok('rw', 'fr')
    ok('sa', 'hi')
    ok('sd', 'en')
    ok('sd-Arab', 'en-Latn')
    ok('si', 'en')
    ok('si-Sinh', 'en-Latn')
    ok('sn', 'en')
    ok('so', 'en')
    ok('sq', 'en')
    ok('st', 'en')
    ok('su', 'id')
    ok('sw', 'en')
    ok('ta', 'en')
    ok('ta-Taml', 'en-Latn')
    ok('te', 'en')
    ok('te-Telu', 'en-Latn')
    ok('tg', 'ru')
    ok('ti', 'en')
    ok('ti-Ethi', 'en-Latn')
    ok('tk', 'ru')
    ok('tk-Latn', 'ru-Cyrl')
    ok('tlh', 'en')
    ok('tn', 'en')
    ok('to', 'en')
    ok('tt', 'ru')
    ok('tum', 'en')
    ok('ug', 'zh')
    ok('ur', 'en')
    ok('ur-Arab', 'en-Latn')
    ok('uz', 'ru')
    ok('uz-Latn', 'ru-Cyrl')
    ok('wo', 'fr')
    ok('xh', 'en')
    ok('yi', 'en')
    ok('yi-Hebr', 'en-Latn')
    ok('yo', 'en')
    ok('zu', 'en')
    sym('sr-Latn', 'sr-Cyrl', 5)
    one('zh-Hans', 'zh-Hant', 15)
    one('zh-Hant', 'zh-Hans', 19)
    sym('zh-Hant-HK', 'zh-Hant-MO', 3)

    return distances

SIMPLE_DISTANCES = _make_simple_distances()


def raw_distance(desired: tuple, supported: tuple):
    # We take in triples of (language, script, region) that can be derived by
    # 'maximizing' a language tag. First of all, if these are identical,
    # return quickly:
    if supported == desired:
        return 0
    if (desired, supported) in _DISTANCE_CACHE:
        return _DISTANCE_CACHE[desired, supported]
    else:
        result = _raw_distance(desired, supported)
        _DISTANCE_CACHE[desired, supported] = result
        return result


def _raw_distance(desired, supported):
    # If these triples match one of the known distances, return that distance.
    # If they share the same last element, remove that last element and keep
    # checking.
    desired_reduced = desired
    supported_reduced = supported
    while desired_reduced:
        if (desired_reduced, supported_reduced) in SIMPLE_DISTANCES:
            return SIMPLE_DISTANCES[desired_reduced, supported_reduced]
        elif desired_reduced[-1] == supported_reduced[-1]:
            desired_reduced = desired_reduced[:-1]
            supported_reduced = supported_reduced[:-1]
        else:
            break

    # The wildcard rules are weird and not even the documentation manages to
    # explain them coherently. The cases where wildcard matches must be the
    # same and where they must be different are very poorly described. The
    # documentation describes a distance between (Portuguese, any-script,
    # Brazil) and (Portuguese, any-other-script, US) where it clearly didn't
    # mean to say "other", and describes a match between nb-FR and nn-DE that
    # doesn't follow its stated rules. You have to extrapolate from the
    # examples what the rules really are.
    #
    # I think what they really are is a series of if-statements, so let's
    # implement those.

    d_lang, d_script, d_region = desired
    s_lang, s_script, s_region = supported

    # There was a rule here that says that Amharic speakers understand
    # British English and no other sort of English. This sounds like a glitch
    # in the generation of languageInfo.xml to me. I'm leaving it out.

    # Traditional and Simplified Chinese are closer than other scripts -- but
    # their distance is still very high, as people don't like dealing with the
    # wrong script.
    if d_lang == s_lang and d_script == 'Hans' and s_script == 'Hant':
        return 15
    if d_lang == s_lang and d_script == 'Hant' and s_script == 'Hans':
        return 19

    # I think the idea here is to add a minor distinction between
    # 'New World Portuguese' and 'Old World Portuguese'.
    if d_lang == 'pt' and s_lang == 'pt' and d_script == s_script:
        if d_region == 'BR' and s_region == 'US':
            return 4
        elif d_region == 'US' and s_region == 'BR':
            return 4
        elif d_region in ('US', 'BR'):
            return 8
        elif s_region in ('US', 'BR'):
            return 8
        else:
            return 4

    # Most English in the world is closer to UK English than to US English.
    # However, based on a comment in the languageInfo.xml file, we'll make
    # US English closer to regions that are US dependencies.
    if d_lang == 'en' and s_lang == 'en' and d_script == s_script:
        if d_region == 'US' and s_region in ('AS', 'GU', 'MH', 'MP', 'PR', 'UM', 'VI'):
            return 4
        elif s_region == 'US' and d_region in ('AS', 'GU', 'MH', 'MP', 'PR', 'UM', 'VI'):
            return 4
        elif d_region == 'US' or s_region == 'US':
            return 6
        elif d_region in ('GB', '001'):
            return 4
        elif s_region in ('001', 'GB'):
            return 4
        else:
            return 5

    # Most Spanish in the world is closer to Latin American Spanish than Spanish Spanish.
    if d_lang == 'es' and s_lang == 'es' and d_script == s_script:
        if d_region == 'ES' or s_region == 'ES':
            return 8
        elif d_region == '419' or s_region == '419':
            return 4
        else:
            return 5

    # Now we're into the most general wildcard matches, where the docs are
    # totally broken. http://unicode.org/reports/tr35/#LanguageMatching has an
    # example about 'nn-DE' and 'nb-FR' where it says it matches '*-*-*', but
    # it actually matches '*' first because 'nn' != 'nb'.
    #
    # We don't want the difference between 'nn' and 'nb' to be 80 just because
    # of a difference in region. So now we have to figure out what the
    # documentation *meant*.
    #
    # What I think it means is that when you match a general wildcard rule, you
    # strip off the last component and keep matching, adding the distance from
    # the matched rule to the result.
    if d_region is not None:
        if d_region != s_region:
            increment = 4
        else:
            increment = 0

        return min(100, increment + raw_distance(
            (d_lang, d_script, None),
            (s_lang, s_script, None)
        ))
    elif d_script is not None:
        # Non-matching script codes add 40 to the distance.
        if d_script != s_script:
            increment = 40
        else:
            increment = 0

        return min(100, increment + raw_distance(
            (d_lang, None, None),
            (s_lang, None, None)
        ))
    else:
        if MACROLANGUAGES.get(d_lang, d_lang) == MACROLANGUAGES.get(s_lang, s_lang):
            # Codes that share a macrolanguage add 20 to the distance.
            return 20
        else:
            # Non-matching language codes add 80 to the distance.
            return 80

