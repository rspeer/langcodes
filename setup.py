from setuptools import setup
import sys

if sys.version_info[0] >= 3:
    print(
        """
        Hey nice, you're on Python 3! You could be running a better,
        thread-safe version of langcodes that's written natively in Python 3.

        Just install `langcodes` instead of `langcodes-py2`.
        """
    )


LONG_DESC = """
langcodes is a toolkit for working with and comparing the standardized codes
for languages, such as 'en' for English and 'zh-Hant' for Traditional Chinese.

The documentation for langcodes lives in its README file, which you can read
on GitHub: https://github.com/LuminosoInsight/langcodes
"""


setup(
    name="langcodes-py2",
    version='1.0',
    maintainer='Luminoso Technologies, Inc.',
    maintainer_email='rspeer@luminoso.com',
    license="MIT",
    url='http://github.com/LuminosoInsight/langcodes',
    platforms=["any"],
    description="Labels and compares human languages in a standardized way",
    long_description=LONG_DESC,
    packages=['langcodes'],
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
