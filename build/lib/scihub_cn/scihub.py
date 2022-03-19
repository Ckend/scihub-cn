# -*- coding: utf-8 -*-

"""
Sci-API Unofficial API
[Search|Download] research papers from [scholar.google.com|sci-hub.io].

@author zaytoun hulei6188
@updated by Python实用宝典
"""
import sys
import re
import asyncio
import hashlib
import logging
import os
import json
from asyncio import ALL_COMPLETED
from datetime import datetime
import random

import aiohttp
import requests
import yaml
from bs4 import BeautifulSoup
from enum import Enum
import argparse
import time
import bibtexparser

# log config
logging.basicConfig()
logger = logging.getLogger('Sci-Hub')
logger.setLevel(logging.INFO)

# constants
SCHOLARS_BASE_URL = 'https://www.sciencedirect.com/search/api'
GOOGLE_SCHOLAR_URL = 'https://scholar.google.com/scholar'
WEB_OF_SCIENCE_URL = 'https://publons.com/publon/list/'
BAIDU_XUESHU_URL = 'https://xueshu.baidu.com/s'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',
}


class NotExistError(Exception):
    """论文找不到的错误"""


class VerifcationError(Exception):
    """搜索时需要验证码"""


class ScholarConf:
    """Helper class for global settings."""

    VERSION = '2.10'
    LOG_LEVEL = 1
    MAX_PAGE_RESULTS = 10  # Current default for per-page results
    SCHOLAR_SITE = 'http://scholar.google.com'

    # USER_AGENT = 'Mozilla/5.0 (X11; U; FreeBSD i386; en-US; rv:1.9.2.9) Gecko/20100913 Firefox/3.6.9'
    # Let's update at this point (3/14):
    USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64; rv:27.0) Gecko/20100101 Firefox/27.0'

    # If set, we will use this file to read/save cookies to enable
    # cookie use across sessions.
    COOKIE_JAR_FILE = None


class ArgumentsError(Exception):
    """参数错误异常"""


class SearchEngine(Enum):
    google_scholar = 1
    baidu_xueshu = 2
    publons = 3
    science_direct = 4


def filter_none(arr):
    """除去数组的空值"""
    return list(filter(lambda _: _, arr))


def construct_download_setting():
    parser = argparse.ArgumentParser(
        prog="scihub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='''
           SciHub to PDF
           ----------------------------------------------------
           使用doi，论文标题，或者bibtex文件批量下载论文

           给出bibtex文件

           $ scihub-cn -i mybibtex.bib --bib

           给出论文doi名称

           $ scihub-cn -d 10.1038/s41524-017-0032-0

           给出论文url

           $ scihub-cn -u https://ieeexplore.ieee.org/document/9429985

           给出论文关键字(关键字之间用_链接,如machine_learning)

           $ scihub-cn -w word1_words2_words3


           给出论文doi的txt文本文件，比如

           ```
           10.1038/s41524-017-0032-0
           10.1063/1.3149495
           ```
           $ scihub-cn -i dois.txt --doi
           给出所有论文名称的txt文本文件

           ```
           Some Title 1
           Some Title 2
           ```
           $ scihub-cn -i titles.txt --title
           给出所有论文url的txt文件
           ```
           url 1
           url 2
           ```
           $ scihub-cn -i urls.txt --url

           你可以在末尾添加-p(--proxy),-o(--output),-e(--engine)，-l(--limit)来指定代理，输出文件夹、搜索引擎以及限制的搜索的条目数
           搜索引擎包括 google_scholar、baidu_xueshu、publons、以及science_direct
           ''')
    parser.add_argument("-u", dest="url", help="input the download url")
    parser.add_argument("-d", dest="doi", help="input the download doi")
    parser.add_argument(
        "--input", "-i",
        dest="inputfile",
        help="input download file",
    )

    parser.add_argument(
        "-w", "--words",
        dest="words",
        help="download from some key words,keywords are linked by _,like machine_learning."
    )
    parser.add_argument("--title",
                        dest="title_file",
                        action="store_true",
                        help="download from paper titles file")
    parser.add_argument(
        "-p", "--proxy",
        dest="proxy",
        help="use proxy to download papers",
    )
    parser.add_argument(
        "--output", "-o",
        dest="output",
        help="setting output path",
    )
    parser.add_argument(
        "--doi",
        dest="doi_file",
        action="store_true",
        help="download paper from dois file",
    )
    parser.add_argument("--bib", action="store_true", dest="bibtex_file", help="download papers from bibtex file")
    parser.add_argument("--url", dest="url_file", action="store_true", help="download paper from url file")
    parser.add_argument("-e", "--engine", dest="search_engine", help="set the search engine")
    parser.add_argument("-l", "--limit", dest="limit", help="limit the number of search result")
    command_args = parser.parse_args()

    if command_args.inputfile:
        setting = DownLoadCommandFileSetting()  # 从命令行得到的文件路径中下载
        if command_args.url_file:
            setting.urls_file = command_args.inputfile
        if command_args.doi_file:
            setting.dois_file = command_args.inputfile
        if command_args.title_file:
            setting.title_file = command_args.inputfile
        if command_args.bibtex_file:
            setting.bibtex_file = command_args.inputfile
        if not setting.urls_file and not setting.dois_file and not setting.title_file and not setting.bibtex_file:
            raise ArgumentsError("error:你没有给出输入文件的类型！")

    else:
        setting = DownLoadCommandSetting()
        if command_args.words:
            setting.words = command_args.words.split('_')
        if command_args.url:
            setting.url = command_args.url
        if command_args.doi:
            setting.doi = command_args.doi
        if not setting.words and not setting.url and not setting.doi:
            setting = DownLoadCommandFileSetting()

    # with open('./config.yml', mode='rt') as f:
    #     res = yaml.load(f, yaml.FullLoader)
    #     try:
    #         setting.search_engine = SearchEngine[res['search-engine']]
    #     except Exception as e:
    #         raise ArgumentsError(
    #             'search-engine must be selected from google_scholar, baidu_xueshu, publons and science_direct')
    #     if 'proxy' in res:
    #         setting.proxy = 'http://' + (res['proxy']['ip'] + ':' + str(res['proxy']['port']))
    #
    #     if 'output' in res:
    #         setting.outputPath = res['output']
    #     if 'limit' in res:
    #         setting.limit = res['limit']

    if command_args.proxy:
        proxy = command_args.proxy
        if not proxy:
            setting.proxy = None
        elif not proxy.startswith('http://') and not proxy.startswith('https://'):
            setting.proxy = 'http://' + command_args.proxy
        else:
            setting.proxy = command_args.proxy

    if command_args.output:
        setting.outputPath = command_args.output
    if command_args.limit:
        setting.limit = int(command_args.limit)
    try:
        if command_args.search_engine:
            setting.search_engine = SearchEngine[command_args.search_engine]
    except Exception as e:
        raise ArgumentsError(
            'search-engine must be selected from GOOGLE_SCHOLAR or BAIDU_XUESHU or PUBLONS or SCIENCE_DIRECT')
    return setting


def main():
    setting = construct_download_setting()
    sh = SciHub(setting.proxy)
    loop = asyncio.get_event_loop()
    infos = []
    for attr, value in vars(setting).items():  # 解析设定中的各个参数
        attr = attr[attr.rfind('__') + 2:]
        if attr in vars(DownLoadSetting).keys() or not value:
            continue

        if isinstance(setting, DownLoadCommandFileSetting):
            if 'bibtex' in attr:
                logger.info("info:开始从配置文件中指定的%s文件中下载..." % value[value.rfind('\\') + 1:])
                infos.extend(sh.generate_paper_info_by_bibtex(value))
            elif 'title' in attr:
                logger.info("info:开始从配置文件中指定的%s文件中下载..." % value[value.rfind('\\') + 1:])
                for title in readline_paper_info(value):
                    infos.extend(sh.search(setting.search_engine, title,
                                           limit=setting.limit,
                                           cookie=setting.cookie))
            else:
                logger.info("info:开始从配置文件中指定的%s文件中下载..." % value[value.rfind('\\') + 1:])
                infos.extend([sh.generate_paper_info(input_) for input_ in readline_paper_info(value)])
        else:
            if 'words' == attr:
                logger.info("info:根据关键字%s开始搜索并下载..." % attr)
                infos.extend(sh.search(setting.search_engine, ' '.join(setting.words),
                                       limit=setting.limit,
                                       cookie=setting.cookie))
            else:
                logger.info("info:根据论文信息%s开始下载..." % attr)
                infos.append(sh.generate_paper_info(value))
    infos = filter_none(infos)
    if len(infos) > 0:
        loop.run_until_complete(
            sh.async_download(asyncio.get_event_loop(), infos, setting.outputPath, proxy=setting.proxy))


def readline_paper_info(file_name):
    res = None
    with open(file_name, mode='rt', encoding='utf8') as f:
        res = f.readlines()
    return [item if not item.endswith('\n') else item[:-1] for item in res]


class SciHub(object):
    """
    SciHub class can search for papers on Google Scholars
    and fetch/download papers from sci-hub.io
    """

    def __init__(self, proxy):
        self.sess = requests.Session()
        self.sess.headers = HEADERS
        self.proxies = self.get_proxies(proxy)
        self.available_base_url_list = self._get_available_scihub_urls()
        self.base_url = self.available_base_url_list[1] + '/'

    def search(self, search_engine, query, limit=10, cookie=''):
        """选择一个搜索引擎搜索内容"""
        if search_engine == SearchEngine.google_scholar:
            return self.search_by_google_scholar(query, limit)
        elif search_engine == SearchEngine.baidu_xueshu:
            return self.search_by_baidu(query, limit)
        elif search_engine == SearchEngine.science_direct:
            return self.search_by_science_direct(query, cookie, limit)
        else:
            return self.search_by_publons(query, limit)

    def _get_available_scihub_urls(self):
        '''
        Finds available scihub urls via http://tool.yovisun.com/scihub/
        '''
        urls = []
        res = self.sess.request(method='GET', url='https://tool.yovisun.com/scihub/', proxies=self.proxies)
        s = self._get_soup(res.content)
        for a in s.find_all('a', href=True):
            if 'sci-hub.' in a['href']:
                urls.append(a['href'])
        return list(set(urls))

    def get_proxies(self, proxy):
        '''
        set proxy for session
        :param proxy_dict:
        :return:
        '''
        if proxy:
            return {
                "http": proxy,
                "https": proxy, }
        return None

    def _change_base_url(self):
        if not self.available_base_url_list:
            raise Exception('Ran out of valid sci-hub urls')
        del self.available_base_url_list[0]
        self.base_url = self.available_base_url_list[0] + '/'
        logger.info("I'm changing to {}".format(self.available_base_url_list[0]))

    def search_by_science_direct(self, query, cookie, limit=10):
        """
        通过science direct搜索，需要配置Cookie
        """
        start = 0
        results = []
        self.sess.headers["Cookie"] = cookie
        while True:
            try:
                res = self.sess.request(method='GET', url=SCHOLARS_BASE_URL,
                                        params={'qs': ' '.join(query), 'offset': start,
                                                "hostname": "www.sciencedirect.com"},
                                        proxies=self.proxies)
            except requests.exceptions.RequestException as e:
                logger.error('Failed to complete search with query %s (connection error)' % query)
                return results
            try:
                s = json.loads(res.content)
            except Exception as e:
                logger.exception(e)
                return results

            papers = s.get('searchResults')
            if not papers:
                return results

            for paper in papers:
                paper_info = self.generate_paper_info(paper['doi'])
                if paper_info:
                    results.append(paper_info)
                    if len(results) >= limit:
                        return results

            start += 25

    def search_by_publons(self, query, limit=10):
        """
        使用publons进行文献搜索
        """
        start = 0
        results = []
        while True:
            try:
                res = self.sess.request(method='GET', url=WEB_OF_SCIENCE_URL,
                                        params={'title': ' '.join(query), 'page': start}, proxies=self.proxies)
            except requests.exceptions.RequestException as e:
                logger.error('Failed to complete search with query %s (connection error)' % query)
                return results

            papers = json.loads(res.content).get("results", [])

            for paper in papers:
                paper_info = self.generate_paper_info(paper['doi'])
                if paper_info:
                    results.append(paper_info)
                    if len(results) >= limit:
                        return results

            start += 1

    def search_by_baidu(self, query, limit=10):
        """
        默认使用百度学术进行文献搜索
        """

        def fetch_doi(url):
            res = self.sess.request(method='GET', url=url, proxies=self.proxies)
            s = self._get_soup(res.content)
            dois = [doi.text.replace("DOI：", "").replace("ISBN：", "").strip() for doi in
                    s.find_all('div', class_='doi_wr')]
            if dois:
                return dois[0]
            else:
                return ""

        start = 0

        results = []
        while True:
            try:
                res = self.sess.request(method='GET', url=BAIDU_XUESHU_URL,
                                        params={'wd': ' '.join(query), 'pn': start, 'filter': 'sc_type%3D%7B1%7D'},
                                        proxies=self.proxies)
            except requests.exceptions.RequestException as e:
                logger.error('Failed to complete search with query %s (connection error)' % query)
                return results

            s = self._get_soup(res.content)
            papers = s.find_all('div', class_="result")

            for paper in papers:
                if not paper.find('table'):
                    link = paper.find('h3', class_='t c_font')
                    url = str(link.find('a')['href'].replace("\n", "").strip())
                    paper_info = self.generate_paper_info(fetch_doi(url))
                    if paper_info:
                        results.append(paper_info)
                        if len(results) >= limit:
                            return results

            start += 10

    def download(self, info, destination='', path=None):
        """
        Downloads a paper from sci-hub given an indentifier (DOI, PMID, URL).
        Currently, this can potentially be blocked by a captcha if a certain
        limit has been reached.
        """
        if 'response' in info:  # 给出的info本身就是一个下载链接时
            res = info['response']
            name = self._generate_name_hash(info['response'])
        else:
            res = self.fetch(info)
            name = info['title'] if info['title'] else self._generate_name_hash(res)

        if type(res) == dict and 'err' in res:
            logger.error(res['err'])
            return
        if not res:
            return
        self._save(res.content,
                   os.path.join(destination, self._vaild_name(name)))

    def fetch(self, info):
        """
        Fetches the paper by first retrieving the direct link to the pdf.
        If the indentifier is a DOI, PMID, or URL pay-wall, then use Sci-Hub
        to access and download paper. Otherwise, just download paper directly.
        """
        try:
            url = None
            if 'doi' in info and info['doi']:
                url = self._get_direct_url(info['doi'])
            else:  # 从scihub网站上有时爬不到论文doi的信息 如文章10.1609/aimag.v18i4.1324
                pattern = re.compile('https?://sci-hub.*?/')
                url = self._get_direct_url(
                    info['scihub_url'][pattern.search(info['scihub_url']).end():]
                )
            # verify=False is dangerous but sci-hub.io
            # requires intermediate certificates to verify
            # and requests doesn't know how to download them.
            # as a hacky fix, you can add them to your store
            # and verifying would work. will fix this later.
            res = self.sess.request(method='GET', url=url, verify=True, proxies=self.proxies)

            if res.headers['Content-Type'] != 'application/pdf':
                self._change_base_url()
                logger.info('由于验证码问题，获取 pdf 失败 论文名称: %s '
                            '(resolved url %s)' % (info['title'], url))
            else:
                return res
        except requests.exceptions.ConnectionError:
            logger.info('Cannot access {}, changing url'.format(self.available_base_url_list[0]))
            self._change_base_url()

        except requests.exceptions.RequestException as e:
            logger.info('由于请求失败，获取pdf失败 论文名称: %s (resolved url %s).'
                        % (info['title'], url))
            return {
                'err': '由于请求失败，获取pdf失败 论文名称:%s (resolved url %s).'
                       % (info['title'], url)
            }

    def _get_direct_url(self, identifier):
        """
        Finds the direct source url for a given identifier.
        """
        id_type = self._classify(identifier)

        return identifier if id_type == 'url-direct' \
            else self._search_direct_url(identifier)

    def _search_direct_url(self, identifier):
        """
        Sci-Hub embeds papers in an iframe. This function finds the actual
        source url which looks something like https://moscow.sci-hub.io/.../....pdf.
        """
        res = self.sess.request(method='GET', url=self.base_url + identifier, verify=False, proxies=self.proxies)
        logger.info(f"获取 {self.base_url + identifier} 中...")
        s = self._get_soup(res.content)
        frame = s.find('iframe') or s.find('embed')
        if frame:
            return frame.get('src') if not frame.get('src').startswith('//') \
                else 'http:' + frame.get('src')

    def _classify(self, identifier):
        """
        Classify the type of identifier:
        url-direct - openly accessible paper
        url-non-direct - pay-walled paper
        pmid - PubMed ID
        doi - digital object identifier
        """
        if (identifier.startswith('http') or identifier.startswith('https')):
            if identifier.endswith('pdf'):
                return 'url-direct'
            else:
                return 'url-non-direct'
        elif identifier.isdigit():
            return 'pmid'
        else:
            return 'doi'

    def _save(self, data, path):
        """
        Save a file give data and a path.
        """
        with open(path, 'wb') as f:
            f.write(data)

    def _get_soup(self, html):
        """
        Return html soup.
        """
        return BeautifulSoup(html, 'html.parser')

    def generate_paper_info(self, identifier):
        """
        根据标识符获得论文的有效信息标识符可以是url或者doi

        """
        if identifier.startswith('http://') or identifier.startswith('https://'):
            check_info = self.check_download_url(identifier)
            if check_info:
                return check_info
        res = self.sess.request(method='GET', url=self.base_url + identifier, verify=False,
                                headers={'User-Agent': ScholarConf.USER_AGENT}, proxies=self.proxies)
        if len(res.content) <= 0:
            return None

        s = self._get_soup(res.content)
        try:
            scihub_url = 'https:' + s.find('div', attrs={'id': 'link'}).find('a').attrs['href']
            citation = s.find(name='div', attrs={'id': 'citation'}, recursive=True)
            title = citation.find('i')
            doi_location = citation.text.find('doi:')
            name = title.text if title else citation.text[:doi_location]
            doi = citation.text[doi_location + 4:-1]
            frame = s.find('iframe') or s.find('embed')
            download_url = None
            if frame:
                download_url = frame.get('src') if not frame.get('src').startswith('//') \
                    else 'http:' + frame.get('src')
        except Exception as e:
            logger.info(identifier + '  scihub数据库不存在这篇论文！')
            return None
        return {'title': name, 'doi': doi, 'scihub_url': scihub_url, 'download_url': download_url}

    def generate_paper_info_by_bibtex(self, bibtex_file_path):
        """
        从bibtex文件中获得论文信息
        Returns:

        """
        with open(bibtex_file_path) as bibtex_file:
            bib_database = bibtexparser.load(bibtex_file)

        res = []
        for info in bib_database.entries:
            if 'title' in info and 'url' in info and 'doi' in info:
                res.append(info)
            else:
                paper_info = None
                if 'doi' in info and not paper_info:
                    paper_info = self.generate_paper_info(info['doi'])
                if 'url' in info and not paper_info:
                    paper_info = self.generate_paper_info(info['url'])
                if not paper_info:
                    res.append(paper_info)
                else:
                    logger.info(info + '该文章信息不全面，无法下载！')
        return res

    def _generate_name_hash(self, res):
        """
        Generate unique filename for paper. Returns a name by calcuating
        md5 hash of file contents, then appending the last 20 characters
        of the url which typically provides a good paper identifier.
        """
        name = res.url.split('/')[-1]
        name = re.sub('#view=(.+)', '', name)
        pdf_hash = hashlib.md5(res.content).hexdigest()
        return '%s-%s' % (pdf_hash, name[-20:])

    def _vaild_name(self, name):
        """
        使得下载的论文名称合法
        """
        if name.endswith('.pdf'):
            name = name[:name.rfind('.pdf')]
        max_len = 223
        name = name.replace('/', ' ').replace('|', ' ').replace('\\', ' ').replace('?',
                                                                                   ' '). \
            replace('<', ' ').replace('>', ' ').replace('*', ' ').replace(':', ' ').replace('"', ' ').replace('-', ' ')
        if len(name) > max_len:
            return name[:max_len] + '.pdf'
        return name + '.pdf'

    def search_by_google_scholar(self, query, limit=10):
        """
        根据论文名称获得论文url 基于google scholar引擎

        """
        i = 0
        results = []

        while True:
            html = self.sess.request(method='GET', url=GOOGLE_SCHOLAR_URL + '?hl=zh-CN&q=' + query + '&start=' + str(i),
                                     headers={'User-Agent': ScholarConf.USER_AGENT}, verify=True, proxies=self.proxies)
            soup = BeautifulSoup(html.text, features='lxml')

            res_set = soup.find_all(
                lambda tag: tag.name == 'a' and tag.has_attr('id') and tag.has_attr('href')
                            and tag.has_attr('data-clk') and tag.has_attr('data-clk-atid') and tag.attrs[
                                'href'].startswith(
                    'http'), recursive=True)
            citations = soup.find_all(lambda tag: tag.name == 'span' and tag.has_attr('class') and tag.attrs[
                'class'][0] == 'gs_ct1' and tag.text == '[引用]', recursive=True)
            if not res_set:
                raise VerifcationError("Error:google scholar 需要人机验证")
            for tag in res_set:
                info = self.generate_paper_info(tag.attrs['href'])
                if info:
                    results.append(info)
                    if len(results) >= limit:
                        return results
            i += 10
            if len(res_set) + len(citations) < 10:  # 谷歌搜索不足10个条目
                break

        return results

    def check_download_url(self, url):
        """查看该链接是否可以直接下载"""
        try:
            response = self.sess.request(method='GET', url=url, headers={'User-Agent': ScholarConf.USER_AGENT},
                                         proxies=self.proxies, timeout=5.5)
            content_type_ = response.headers['Content-Type']
            if content_type_.find('text/html') < 0 and content_type_.find('application') >= 0:
                logger.info(url + '这是一个直接可以下载的链接！')
                return {'base_url': url, 'response': response}
        except Exception as e:
            return None
        return None

    async def async_get_direct_url(self, identifier, proxy=None):
        """
        异步获取scihub直链
        """

        async with aiohttp.ClientSession() as sess:
            async with sess.request(method='GET', url=self.base_url + identifier,
                                    headers={'User-Agent': ScholarConf.USER_AGENT}) as res:
                logger.info(f"获取 {self.base_url + identifier} 中...")
                # await 等待任务完成
                html = await res.text(encoding='utf-8')
                s = self._get_soup(html)
                frame = s.find('iframe') or s.find('embed')
                if frame:
                    return frame.get('src') if not frame.get('src').startswith('//') \
                        else 'http:' + frame.get('src')
                else:
                    logger.error("Error: 可能是 Scihub 上没有收录该文章, 请直接访问上述页面看是否正常。")
                    return html

    async def job(self, session, info, destination='', proxy=None, path=None):
        """
        异步下载文件
        """
        res = None
        if 'response' in info:  # 论文本身不需要下载
            res = info['response'].content
            name = self._generate_name_hash(info['response'])
        else:
            try:
                logger.info(f"获取 {info['scihub_url']} 中...")
                url_handler = await session.get(info['download_url'], proxy=proxy)
                res = await url_handler.read()
            except Exception as e:
                logger.error(f"获取源文件出错: {e}，大概率是下载超时，请检查")

            name = info['title'] if 'title' in info and info['title'] else hashlib.md5(
                bytes(info['download_url'].split("/")[-1].split("#")[0], encoding="utf8")).hexdigest()

        if not res:
            return

        self._save(res,
                   os.path.join(destination, self._vaild_name(name)))

    async def async_download(self, loop, infos, destination='', proxy=None, path=None):
        """
        触发异步下载任务
        """
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=600),
                                         headers={'User-Agent': ScholarConf.USER_AGENT}) as session:
            # 建立会话session
            tasks = [loop.create_task(self.job(session, info, destination, proxy, path)) for info in infos]
            # 建立所有任务
            finished, unfinished = await asyncio.wait(tasks)
            # 触发await，等待任务完成
            [r.result() for r in finished]


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


if __name__ == '__main__':
    main()
