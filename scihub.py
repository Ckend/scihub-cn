# -*- coding: utf-8 -*-

"""
Sci-API Unofficial API
[Search|Download] research papers from [scholar.google.com|sci-hub.io].

@author zaytoun
@updated by Python实用宝典
"""
import sys
import re
import asyncio
import hashlib
import logging
import os
import json
import aiohttp
import requests
import yaml
from bs4 import BeautifulSoup
from scholar import SearchScholarQuery, ScholarQuerier
from enum import Enum
import argparse
import time

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


class SearchEngine(Enum):
    google_scholar = 1
    baidu_xueshu = 2
    publons = 3
    science_direct = 4


def construct_download_setting():
    parser = argparse.ArgumentParser(
        prog="scihub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='''
           SciHub to PDF
           ----------------------------------------------------
           使用doi，论文标题，或者bibtex文件批量下载论文

           给出bibtex文件

           $ scihub.py -i input.bib --bib

           给出论文doi名称

           $ scihub.py -d 10.1038/s41524-017-0032-0

           给出论文url

           $ scihub.py -u https://ieeexplore.ieee.org/document/9429985
           
           给出论文关键字(关键字之间用_链接)
           
           $ scihub.py -w word1_words2_words3


           给出论文doi的txt文本文件，荣誉

           ```
           10.1038/s41524-017-0032-0
           10.1063/1.3149495
           ```
           $ scihub.py -i dois.txt --doi
           给出所有论文名称的txt文本文件

           ```
           Some Title 1
           Some Title 2
           ```
           $ scihub.py -i titles.txt --title
           给出所有论文url的txt文件
           ```
           url 1
           url 2
           ```
           $ scihub.py -i urls.txt --url
           
           你可以在末尾添加-p(--proxy),-o(--output),-e(--engine)来指定代理，输出文件夹以及搜索引擎
           ''')
    parser.add_argument("-u", dest="url", help="input the download url")
    parser.add_argument("-d", dest="doi", help="input the download doi")
    parser.add_argument(
        "--input", "-i",
        dest="inputfile",
        help="input download file",
    )
    parser.add_argument("--bib",
                        dest="bibtex_file", help="download papers from the bibtex file")

    parser.add_argument(
        "-w",
        dest="words",
        action="store_true",
        help="download from some key words"
    )
    parser.add_argument("--title",
                        dest="title_file",
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
    parser.add_argument("--url", dest="url_file", action="store_true", help="download paper from url file")
    parser.add_argument("-e", "--engine", dest="search_engine", help="set the search engine")
    command_args = parser.parse_args()

    if command_args.inputfile:
        setting = DownLoadCommandFileSetting()  # 从命令行得到的文件路径中下载
        if command_args.url_file:
            setting.urls_file = command_args.inputfile
        elif command_args.doi_file:
            setting.dois_file = command_args.inputfile
        elif command_args.title_file:
            setting.title_file = command_args.inputfile
        elif command_args.bibtex_file:
            setting.bibtex_file = command_args.inputfile
        else:
            logger.error("error:你没有给出输入文件的类型！")
            return None
    else:
        setting = DownLoadCommandSetting()
        if command_args.words:
            setting.words = command_args.words.split('_')
        elif command_args.url:
            setting.url = command_args.url
        elif command_args.doi:
            setting.doi = command_args.doi
        else:
            logger.error("error:你没有给出提示信息！")
    with open('./config.yml', mode='rt') as f:
        res = yaml.load(f)
        try:
            setting.search_engine = SearchEngine[res['search-engine']]
        except Exception as e:
            logger.error(
                'search-engine must be selected from GOOGLE_SCHOLAR or BAIDU_XUESHU or PUBLONS or SCIENCE_DIRECT')
            return None
        if 'proxy' in res:
            setting.proxy = (res['proxy']['ip'] + ':' + str(res['proxy']['port']))

        if 'output' in res:
            setting.outputPath = res['output']

    if command_args.proxy:
        setting.proxy = command_args.proxy
    if command_args.output:
        setting.outputPath = command_args.output
    if command_args.search_engine:
        setting.search_engine = command_args.search_engine

    return setting


def download_command():
    setting = construct_download_setting()

    # setting.words = ['machine']
    sh = SciHub()
    sh.set_proxy(setting.proxy)
    for attr, value in vars(setting).items():
        attr = attr[attr.rfind('__') + 2:]
        if attr in vars(DownLoadSetting).keys() or not value:
            continue
        if 'words' == attr:
            for info in sh.search(setting.search_engine, ' '.join(value), cookie=setting.cookie, limit=10):
                sh.download(info, setting.outputPath)
            continue
        if isinstance(setting, DownLoadCommandFileSetting):
            if 'bibtex' in attr:
                pass
            elif 'title' in attr:
                for title in readline_paper_info(value):
                    for info in sh.search(setting.search_engine, title, cookie=setting.cookie, limit=10):
                        sh.download(info, setting.outputPath)
            else:
                for input_ in readline_paper_info(value):
                    sh.download(sh.generate_paper_info(input_), setting.outputPath)
        else:
            sh.download(sh.generate_paper_info(value), setting.outputPath)


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

    def __init__(self):
        self.sess = requests.Session()
        self.sess.headers = HEADERS
        self.available_base_url_list = self._get_available_scihub_urls()
        self.base_url = self.available_base_url_list[0] + '/'

    def search(self, search_engine, query, limit=10, cookie=''):
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
        res = requests.get('http://tool.yovisun.com/scihub/')
        s = self._get_soup(res.content)
        for a in s.find_all('a', href=True):
            if 'sci-hub.' in a['href']:
                urls.append(a['href'])
        return urls

    def set_proxy(self, proxy):
        '''
        set proxy for session
        :param proxy_dict:
        :return:
        '''
        if proxy:
            self.sess.proxies = {
                "http": proxy,
                "https": proxy, }

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
                res = self.sess.get(SCHOLARS_BASE_URL, params={'qs': ' '.join(query), 'offset': start,
                                                               "hostname": "www.sciencedirect.com"})
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
                results.append(self._generate_name_hash(paper['doi']))
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
                res = self.sess.get(WEB_OF_SCIENCE_URL, params={'title': ' '.join(query), 'page': start})
            except requests.exceptions.RequestException as e:
                logger.error('Failed to complete search with query %s (connection error)' % query)
                return results

            papers = json.loads(res.content).get("results", [])

            for paper in papers:
                results.append(self.generate_paper_info(paper['doi']))
                if len(results) >= limit:
                    return results

            start += 1

    def search_by_baidu(self, query, limit=10):
        """
        默认使用百度学术进行文献搜索
        """

        def fetch_doi(url):
            res = self.sess.get(url)
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
                res = self.sess.get(BAIDU_XUESHU_URL,
                                    params={'wd': ' '.join(query), 'pn': start, 'filter': 'sc_type%3D%7B1%7D'})
            except requests.exceptions.RequestException as e:
                logger.error('Failed to complete search with query %s (connection error)' % query)
                return results

            s = self._get_soup(res.content)
            papers = s.find_all('div', class_="result")

            for paper in papers:
                if not paper.find('table'):
                    link = paper.find('h3', class_='t c_font')
                    url = str(link.find('a')['href'].replace("\n", "").strip())
                    results.append(self.generate_paper_info(fetch_doi(url)))
                    if len(results) >= limit:
                        return results

            start += 10

    def download(self, info, destination='', path=None):
        """
        Downloads a paper from sci-hub given an indentifier (DOI, PMID, URL).
        Currently, this can potentially be blocked by a captcha if a certain
        limit has been reached.
        """
        name = None
        res = None
        if 'response' in info:  # 论文本身不需要下载
            res = info['response']
            name = self._generate_name_hash(info['response'])
        else:
            res = self.fetch(info)
            name = info['name'] if info['name'] else self._generate_name_hash(res)

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
            indirect_url = None
            if 'doi' in info and info['doi']:
                url = self._get_direct_url(info['doi'])
            else:
                pattern = re.compile('https?://sci-hub.*?/')
                url = self._get_direct_url(
                    info['scihub_url'][pattern.search(info['scihub_url']).end():]
                )
            # verify=False is dangerous but sci-hub.io
            # requires intermediate certificates to verify
            # and requests doesn't know how to download them.
            # as a hacky fix, you can add them to your store
            # and verifying would work. will fix this later.
            res = self.sess.get(url, verify=True)

            if res.headers['Content-Type'] != 'application/pdf':
                self._change_base_url()
                logger.info('由于验证码问题，获取 pdf 失败 论文名称: %s '
                            '(resolved url %s)' % (info['name'], url))
            else:
                return res
        except requests.exceptions.ConnectionError:
            logger.info('Cannot access {}, changing url'.format(self.available_base_url_list[0]))
            self._change_base_url()

        except requests.exceptions.RequestException as e:
            logger.info('由于请求失败，获取pdf失败 论文名称: %s (resolved url %s).'
                        % (info['name'], url))
            return {
                'err': '由于请求失败，获取pdf失败 论文名称:%s (resolved url %s).'
                       % (info['name'], url)
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
        res = self.sess.get(self.base_url + identifier, verify=False)
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
        res = self.sess.get(self.base_url + identifier, verify=True)
        s = self._get_soup(res.content)
        try:
            scihub_url = 'https:' + s.find('div', attrs={'id': 'link'}).find('a').attrs['href']
            citation = s.find(name='div', attrs={'id': 'citation'}, recursive=True)
            title = citation.find('i')
            doi_location = citation.text.find('doi:')
            name = title.text if title else citation.text[:doi_location]
            doi = citation.text[doi_location + 4:-1]
        except Exception as e:
            logger.info(identifier + '  scihub数据库不存在这篇论文！')
            return None
        return {'name': name, 'doi': doi, 'scihub_url': scihub_url}

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
        max_len = 252
        name = name.replace('/', ' ').replace('|', ' ').replace('\\', ' ').replace('?',
                                                                                   ' '). \
            replace('<', ' ').replace('>', ' ').replace('*', ' ').replace(':', ' ').replace('"', ' ')
        if len(name) > max_len:
            return name[:max_len] + '.pdf'
        return name + '.pdf'

    def search_by_google_scholar(self, query, limit=10):
        """
        根据论文名称获得论文url 基于google scholar引擎

        """
        i = 0
        results = []
        while limit > 0:
            html = self.sess.get(url=GOOGLE_SCHOLAR_URL + '?hl=zh-CN&q=' + query + '&start=' + str(i),
                                 headers={'User-Agent': ScholarConf.USER_AGENT}, verify=True)

            soup = BeautifulSoup(html.text, features='lxml')

            res_set = soup.find_all(
                lambda tag: tag.name == 'a' and tag.has_attr('id') and tag.has_attr('href')
                            and tag.has_attr('data-clk') and tag.has_attr('data-clk-atid') and tag.attrs[
                                'href'].startswith(
                    'http'), recursive=True)
            if not res_set:
                logger.error("Error:google scholar 需要人机验证")
                return None

            j = 0
            for tag in res_set:
                base_url = tag.attrs['href']
                response = self.sess.get(base_url, headers={'User-Agent': ScholarConf.USER_AGENT}, verify=True)
                content_type_ = response.headers['Content-Type']
                check_info = self.check_download_url(base_url)
                if check_info:
                    results.append(check_info)
                    continue
                info = self.generate_paper_info(base_url)
                if info:  # 在scihub数据库能查到该论文时
                    info['base_url'] = base_url
                    results.append(info)
                    j += 1
            i += 10
            limit -= j
            if len(res_set) < 10:  # 谷歌搜索不足10个条目
                break
            time.sleep(0.5)

        return results

    def check_download_url(self, url):
        response = self.sess.get(url, headers={'User-Agent': ScholarConf.USER_AGENT}, verify=True)
        content_type_ = response.headers['Content-Type']
        if content_type_.find('text/html') < 0 and content_type_.find('application') >= 0:
            logger.info(url + '这是一个直接可以下载的链接！')
            return {'base_url': url, 'response': response}
        return None

    async def async_get_direct_url(self, identifier):
        """
        异步获取scihub直链
        """

        async with aiohttp.ClientSession() as sess:
            async with sess.get(self.base_url + identifier) as res:
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

    async def job(self, session, url, destination='', path=None):
        """
        异步下载文件
        """

        if not url:
            return
        file_name = url.split("/")[-1].split("#")[0]
        logger.info(f"正在读取并写入 {file_name} 中...")
        # 异步读取内容
        try:
            url_handler = await session.get(url)
            content = await url_handler.read()
        except Exception as e:
            logger.error(f"获取源文件出错: {e}，大概率是下载超时，请检查")
            return str(url)
        with open(os.path.join(destination, path + file_name), 'wb') as f:
            # 写入至文件
            f.write(content)
        return str(url)

    async def async_download(self, loop, urls, destination='', path=None):
        """
        触发异步下载任务
        """
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=600)) as session:
            # 建立会话session
            tasks = [loop.create_task(self.job(session, url, destination, path)) for url in urls]
            # 建立所有任务
            finished, unfinished = await asyncio.wait(tasks)
            # 触发await，等待任务完成
            [r.result() for r in finished]


class DownLoadSetting:

    def __init__(self) -> None:
        super().__init__()
        self.__outputPath = None
        self.__proxy = None
        self.search_engine = SearchEngine.google_scholar
        self.__cookie = ''

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
        self.__dois = None
        self.__urls = None

    @property
    def doi(self):
        return self.__doi

    @doi.setter
    def doi(self, doi):
        self.__doi = doi

    @property
    def url(self):
        return self.__doi

    @url.setter
    def url(self, url):
        self.__url = url

    @property
    def words(self):
        return self.__doi

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
    download_command()
