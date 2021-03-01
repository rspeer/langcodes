from setuptools import setup
import sys

if sys.version_info[0] < 3:
    print(
        """
        Sorry for the inconvenience, but langcodes is native Python 3 code,
        and you're running Python 2.
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
    version='3.1.0',
    maintainer='Robyn Speer',
    maintainer_email='rspeer@luminoso.com',
    license="MIT",
    url='http://github.com/LuminosoInsight/langcodes',
    platforms=["any"],
    description="Labels and compares human languages in a standardized way",
    long_description=LONG_DESC,
    packages=['langcodes'],
    include_package_data=True,
    install_requires=[],
    python_requires='>=3.6',
    tests_require=['pytest'],
    extras_require={
        'data': 'language_data >= 1.0'
    },
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
