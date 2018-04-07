from setuptools import setup
import sys

if sys.version_info[0] >= 3:
    print(
        """
        Hey nice, you're on Python 3! You could be running a better
        version of langcodes that's written natively in Python 3.

        Just install `langcodes` instead of `langcodes-py2`.
        """
    )


LONG_DESC = """
langcodes is a toolkit for working with and comparing the standardized codes
for languages, such as 'en' for English, 'es' for Spanish, and 'zh-Hant' for
Traditional Chinese. These are BCP 47 language codes, formerly known as ISO
language codes.

langcodes is designed for Python 3, but this version of langcodes,
'langcodes-py2', is a backport to Python 2.7.

The documentation for langcodes lives in its README file, which you can read
on GitHub: https://github.com/LuminosoInsight/langcodes
"""


setup(
    name="langcodes-py2",
    version='1.2.1',
    maintainer='Luminoso Technologies, Inc.',
    maintainer_email='rspeer@luminoso.com',
    license="MIT",
    url='http://github.com/LuminosoInsight/langcodes',
    platforms=["any"],
    description="Labels and compares human languages in a standardized way -- Python 2 backport",
    long_description=LONG_DESC,
    packages=['langcodes'],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
