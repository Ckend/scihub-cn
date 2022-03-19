#!/usr/bin/env python
# coding: utf-8
import io
import os
import requests
from setuptools import setup

# 将markdown格式转换为rst格式
def md_to_rst(from_file, to_file):
    r = requests.post(url='http://c.docverter.com/convert',
                      data={'to': 'rst', 'from': 'markdown'},
                      files={'input_files[]': open(from_file, 'rb')})
    if r.ok:
        with open(to_file, "wb") as f:
            f.write(r.content)


md_to_rst("README.md", "README.rst")

if os.path.exists('README.rst'):
    long_description = open('README.rst', encoding="utf-8").read()
else:
    long_description = 'Add a fallback short description here'

if os.path.exists("requirements.txt"):
    install_requires = io.open("requirements.txt").read().split("\n")
else:
    install_requires = []

setup(
    name='scihub-cn',
    version='0.0.11',
    author='ckend',
    author_email='admin@pythondict.com',
    url='https://github.com/Ckend/scihub-cn',
    description='中文环境下可用的全网文献下载工具',
    long_description=long_description,
    long_description_content_type="text/x-rst",
    packages=['scihub_cn'],
    install_requires=[
        "beautifulsoup4==4.10.0",
        "requests==2.26.0",
        "retrying==1.3.3",
        "PyYaml==5.4",
        "bibtexparser==1.2.0",
        "aiohttp==3.8.1",
        "lxml==4.7.1",
    ],
    entry_points={
        "console_scripts": ['scihub-cn=scihub_cn.scihub:main']
    },
)
