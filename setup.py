from setuptools import setup
import sys

if sys.version_info[0] < 3:
    print(
        """
        Sorry for the inconvenience, but langcodes is native Python 3 code,
        and you're running Python 2.

        If you need to run it on Python 2, there's a backport to Python 2.7 in
        a separate package called `langcodes-py2`.
        """
    )
    sys.exit(1)


LONG_DESC = """
langcodes is a toolkit for working with and comparing the standardized codes
for languages, such as 'en' for English, 'es' for Spanish, and 'zh-Hant' for
Traditional Chinese. These are BCP 47 language codes, formerly known as ISO
language codes.

The documentation for langcodes lives in its README file, which you can read
on GitHub: https://github.com/LuminosoInsight/langcodes
"""


setup(
    name="langcodes",
    version='1.3.0',
    maintainer='Luminoso Technologies, Inc.',
    maintainer_email='rspeer@luminoso.com',
    license="MIT",
    url='http://github.com/LuminosoInsight/langcodes',
    platforms=["any"],
    description="Labels and compares human languages in a standardized way",
    long_description=LONG_DESC,
    packages=['langcodes'],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
