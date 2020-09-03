import string
import langcodes

# Iterate through all 2- and 3-letter language codes, and for all languages
# that have enough data to represent their own name, show:
#
# - The original code
# - The code after normalization
# - The language's name in English
# - The language's name in that language (its autonym)

en = langcodes.get('en')

for let1 in string.ascii_lowercase:
    for let2 in string.ascii_lowercase:
        for let3 in [''] + list(string.ascii_lowercase):
            code = let1 + let2 + let3
            lcode = langcodes.get(code)
            if lcode.has_name_data():
                autonym = lcode.autonym()
                name = lcode.language_name()
                print('%-3s %-3s %-30s %s' % (code, lcode.language, name, autonym))
