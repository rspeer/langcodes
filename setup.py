from setuptools import setup

setup(
    name="langcodes",
    version='0.1',
    maintainer='Luminoso Technologies, Inc.',
    maintainer_email='info@luminoso.com',
    license="MIT",
    url='http://github.com/LuminosoInsight/langcodes',
    platforms=["any"],
    description="Labels and compares human languages in a standards-compliant way",
    packages=['langcodes'],
    package_data={'langcodes': ['data/*.txt', 'data/cldr/*.json', 'data/cldr/*/*.json']},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
