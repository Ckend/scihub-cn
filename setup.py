#!/usr/bin/env python
# coding: utf-8

from setuptools import setup

setup(
    name='scihub-cn',
    version='0.0.5',
    author='ckend',
    author_email='admin@pythondict.com',
    url='https://github.com/Ckend/scihub-cn',
    description=u'全网文献下载工具',
    packages=['scihub_cn'],
    install_requires=[
        "beautifulsoup4==4.10.0",
        "requests==2.26.0",
        "retrying==1.3.3",
        "pysocks==1.7.1",
        "PyYaml==5.4",
        "bibtexparser==1.2.0",
        "aiohttp==3.8.1",
        "lxml==4.7.1",
    ],
    entry_points={
        "console_scripts": ['scihub-cn=scihub_cn.scihub:main']
    },
)
