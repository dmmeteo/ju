import os
from shutil import copyfile

from setuptools import setup

src = os.path.join(os.path.dirname(__file__), 'jurc-example')
dst = os.path.expanduser('~/.jurc')
if not os.path.isfile(dst):
    copyfile(src, dst)

setup(
    name='ju',
    version='0.3',
    author="Dmitry Sichkar",
    author_email="dmmeteo@gmail.com",
    license="MIT",
    py_modules=['ju'],
    zip_safe=False,
    install_requires=[
        'setuptools',
        'Click',
        'jira',
        'python-hglib',
        'colorama'
    ],
    python_requires=">=2.7.14, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, <4",
    entry_points={"console_scripts": ["ju=ju.cli:cli"]}
)
