# -*- coding: utf-8 -*-
from dataclasses import dataclass
from enum import Enum


@dataclass
class PaperInfo:
    url: str
    title: str
    doi: str
    publisher: str
    authors: str


@dataclass
class PaperDetailDescription:
    authors: str
    title: str
    publisher: str
    doi: str


class SearchEngine(Enum):
    google_scholar = 1
    baidu_xueshu = 2
    publons = 3
    science_direct = 4


class DownLoadSetting:

    def __init__(self) -> None:
        super().__init__()
        self.__outputPath = "./"
        self.__proxy = None
        self.__search_engine = SearchEngine.baidu_xueshu
        self.__cookie = ''
        self.__limit = 10

    @property
    def limit(self):
        return self.__limit

    @limit.setter
    def limit(self, limit):
        self.__limit = limit

    @property
    def cookie(self):
        return self.__cookie

    @cookie.setter
    def cookie(self, cookie):
        self.__cookie = cookie

    @property
    def search_engine(self):
        return self.__search_engine

    @search_engine.setter
    def search_engine(self, search_engine):
        self.__search_engine = search_engine

    @property
    def outputPath(self):
        return self.__outputPath

    @outputPath.setter
    def outputPath(self, outputPath):
        self.__outputPath = outputPath

    @property
    def proxy(self):
        return self.__proxy

    @proxy.setter
    def proxy(self, proxy):
        self.__proxy = proxy


class DownLoadCommandSetting(DownLoadSetting):

    def __init__(self) -> None:
        super().__init__()
        self.__doi = None
        self.__url = None
        self.__words = None

    @property
    def doi(self):
        return self.__doi

    @doi.setter
    def doi(self, doi):
        self.__doi = doi

    @property
    def url(self):
        return self.__url

    @url.setter
    def url(self, url):
        self.__url = url

    @property
    def words(self):
        return self.__words

    @words.setter
    def words(self, words):
        self.__words = words


class DownLoadCommandFileSetting(DownLoadSetting):

    def __init__(self) -> None:
        super().__init__()
        self.__bibtex_file = None
        self.__dois_file = None
        self.__urls_file = None
        self.__title_file = None

    @property
    def bibtex_file(self):
        return self.__bibtex_file

    @bibtex_file.setter
    def bibtex_file(self, bibtex_file):
        self.__bibtex_file = bibtex_file

    @property
    def dois_file(self):
        return self.__dois_file

    @dois_file.setter
    def dois_file(self, dois_file):
        self.__dois_file = dois_file

    @property
    def urls_file(self):
        return self.__urls_file

    @urls_file.setter
    def urls_file(self, urls_file):
        self.__urls_file = urls_file

    @property
    def title_file(self):
        return self.__title_file

    @title_file.setter
    def title_file(self, title_file):
        self.__title_file = title_file
