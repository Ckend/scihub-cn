#!/usr/bin/env python
# coding: utf-8
import io
import os
import requests
from setuptools import setup

long_description = open('README.md', encoding="utf-8").read()

if os.path.exists("requirements.txt"):
    install_requires = io.open("requirements.txt").read().split("\n")
else:
    install_requires = []

setup(
    name='scihub-cn',
    version='0.0.16',
    author='ckend',
    author_email='admin@pythondict.com',
    url='https://github.com/Ckend/scihub-cn',
    description='中文环境下可用的全网文献下载工具',
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=['scihub_cn'],
    install_requires=install_requires,
    entry_points={
        "console_scripts": ['scihub-cn=scihub_cn.scihub:main']
    },
)
