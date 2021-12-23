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


def construct_download_setting():
    parser = argparse.ArgumentParser(
        prog="sichub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='''
           SciHub to PDF
           ----------------------------------------------------
           使用doi，论文标题，或者bibtex文件批量下载论文

           给出bibtex文件

           $ scihub.py -i input.bib

           给出论文doi名称

           $ scihub.py 10.1038/s41524-017-0032-0

           给出论文url

           $ scihub.py https://ieeexplore.ieee.org/document/9429985

           给出论文名称

           $ scihub.py  paper_name

           给出论文doi的txt文本文件，荣誉

           ```
           10.1038/s41524-017-0032-0
           10.1063/1.3149495
           .....
           ```
           ```
           $ scihub.py -i dois.txt --doi
           ```
           给出所有论文名称的txt文本文件

           ```
           Some Title 1
           Some Title 2
           .....
           ```
           ```
           $ scihub.py -i titles.txt --title
           ```
           给出所有论文url的txt文件
           ```
           url 1
           url 2
           ```
           $ scihub.py -i urls.txt --url
           ''')
    parser.add_argument(
        "--input", "-i",
        dest="inputfile",
        help="bibtex input file",
    )
    parser.add_argument(
        "-t",
        dest="title",
        action="store_true",
        help="download from paper title"
    )
    parser.add_argument("--title",
                        dest="title",
                        help="download from paper titles file")
    parser.add_argument(
        "--p",
        dest="proxy",
        help="use proxy to download papers",
    )
    parser.add_argument(
        "--location", "-l",
        help="folder, ex: -l 'folder/'",
    )
    parser.add_argument(
        "--doi",
        dest="doi",
        action="store_true",
        help="download paper from dois file",
    )
    parser.add_argument("url", dest="url", action="store_true", help="download paper from url file")
    command_args = parser.parse_args()
    pattern = re.compile(r'.*/.*')
    arg = sys.argv[1]
    setting = None
    if not command_args.inputfile:
        setting = DownLoadCommandSetting()  # 从命令行参数下载
        end = len(sys.argv)
        for i in range(1, len(sys.argv)):
            if sys.argv[i].startswith('-'):
                end = i
                break
        if arg.startswith('http') or arg.startswith('https'):
            for i in range(1, end):
                if not arg.startswith('http') and not arg.startswith('https'):
                    logger.error('输入的url有误，请重新输入')
                    return None
            if end > 2:  # 有多个url参数
                setting.urls = sys.argv[1:end]
            else:
                setting.url = arg
        elif pattern.match(arg):
            for i in range(1, end):
                if not pattern.match(sys.argv[i]):
                    logger.error('输入的doi有误，请重新输入')
                    return None
            if end > 2:  # 有多个个doi参数
                setting.dois = sys.argv[1:end]
            else:
                setting.doi = arg
        else:
            if end > 2:
                setting.words = sys.argv[1:end]

    else:
        setting = DownLoadCommandFileSetting()  # 从命令行得到的文件路径中下载
        if command_args.url:
            setting.urls_file = command_args.inputfile
        elif command_args.doi:
            setting.dois_file = command_args.inputfile
        elif command_args.title:
            setting.title_file = command_args.inputfile
        else:
            setting.bibtex_file = command_args.inputfile

    with open('./config.yml', mode='rt') as f:
        res = yaml.load(f)
        try:
            setting.downloadChannel = (DownLoadSetting.Channel[res['download_channel']])
        except Exception as e:
            logger.error(
                'Download channels must be selected from GOOGLE_SCHOLAR or BAIDU_XUESHU or PUBLONS or SCIENCE_DIRECT')
            return None
        if 'proxy' in res:
            setting.proxy = (res['proxy']['ip'] + ':' + res['proxy']['port'])

        if 'output' in res:
            setting.outputPath = res['output']
        else:
            setting.outputPath = DownLoadSetting.DEFAULT_OUTPUT_PATH
    return setting


def download_command():
    # setting = construct_download_setting()
    setting = DownLoadCommandSetting()
    setting.outputPath = r'C:\Users\胡磊\Desktop\paper'
    setting.url = 'https://ieeexplore.ieee.org/abstract/document/8770530'
    sh = SciHub()
    for attr, value in vars(setting).items():
        if 'words' in attr:
            sh.download(sh.search_by_google_scholar(' '.join(value), limit=10), setting.outputPath)
            continue
        if isinstance(setting, DownLoadCommandFileSetting):
            if 'bibtex' in attr:
                pass
            elif 'title' in attr:
                for title in readline_paper_info(value):
                    sh.download(sh.search_by_google_scholar(title), setting.outputPath)
            else:
                for input_ in readline_paper_info(value):
                    sh.download(sh.generate_paper_info(input_), setting.outputPath)
        if isinstance(value, list):
            for input_ in value:
                sh.download(sh.generate_paper_info(input_), setting.outputPath)
        else:
            sh.download(sh.generate_paper_info(value), setting.outputPath)


def readline_paper_info(file_name):
    res = None
    with open(file_name, mode='rt', encoding='utf8') as f:
        res = f.readlines()
    return res


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
        results = {'papers': []}
        self.sess.headers["Cookie"] = cookie
        while True:
            try:
                res = self.sess.get(SCHOLARS_BASE_URL, params={'qs': query, 'offset': start,
                                                               "hostname": "www.sciencedirect.com"})
            except requests.exceptions.RequestException as e:
                results['err'] = 'Failed to complete search with query %s (connection error)' % query
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
                source = paper.get("link")
                source_name = paper.get('sourceTitle')

                results['papers'].append({
                    'name': source_name,
                    'url': f"https://www.sciencedirect.com{source}",
                    'doi': paper['doi']
                })

                if len(results['papers']) >= limit:
                    return results

            start += 25

    def search_by_publons(self, query, limit=10):
        """
        使用publons进行文献搜索
        """
        start = 0
        results = {'papers': []}
        while True:
            try:
                res = self.sess.get(WEB_OF_SCIENCE_URL, params={'title': query, 'page': start})
            except requests.exceptions.RequestException as e:
                results['err'] = 'Failed to complete search with query %s (connection error)' % query
                return results

            papers = json.loads(res.content).get("results", [])

            for paper in papers:
                name = paper['publon']['name']
                link = f"https://publons.com/{paper['publon']['url']}#{name}"
                doi = paper['altmetric_score']['doi']

                results['papers'].append({
                    'name': name,
                    'url': link,
                    'doi': doi,
                })

                if len(results['papers']) >= limit:
                    return results

            start += 1

    def search(self, query, limit=10):
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

        results = {'papers': []}
        while True:
            try:
                res = self.sess.get(BAIDU_XUESHU_URL, params={'wd': query, 'pn': start, 'filter': 'sc_type%3D%7B1%7D'})
            except requests.exceptions.RequestException as e:
                results['err'] = 'Failed to complete search with query %s (connection error)' % query
                return results

            s = self._get_soup(res.content)
            papers = s.find_all('div', class_="result")

            for paper in papers:
                if not paper.find('table'):
                    link = paper.find('h3', class_='t c_font')
                    url = str(link.find('a')['href'].replace("\n", "").strip())
                    doi = fetch_doi(url)
                    if doi:
                        results['papers'].append({
                            'name': link.text,
                            'url': url,
                            'doi': fetch_doi(url),
                        })

                    if len(results['papers']) >= limit:
                        return results

            start += 10

    def download(self, info, destination='', path=None):
        """
        Downloads a paper from sci-hub given an indentifier (DOI, PMID, URL).
        Currently, this can potentially be blocked by a captcha if a certain
        limit has been reached.
        """
        name = None
        if 'response' in info:  # 论文本身不需要下载
            data = info['response'].content
            name = self._generate_name_hash(info['response'])
        else:
            data = self.fetch(info)
            name = info['name']

        if not data:
            return
        if not 'err' in data:
            self._save(data['pdf'],
                       os.path.join(destination, self.vaild_name(name)))

        return data

    def fetch(self, info):
        """
        Fetches the paper by first retrieving the direct link to the pdf.
        If the indentifier is a DOI, PMID, or URL pay-wall, then use Sci-Hub
        to access and download paper. Otherwise, just download paper directly.
        """
        try:
            url = self._get_direct_url(info['doi'])

            # verify=False is dangerous but sci-hub.io
            # requires intermediate certificates to verify
            # and requests doesn't know how to download them.
            # as a hacky fix, you can add them to your store
            # and verifying would work. will fix this later.
            res = self.sess.get(url, verify=False)

            if res.headers['Content-Type'] != 'application/pdf':
                self._change_base_url()
                logger.info('由于验证码问题，获取 pdf 失败 论文名称: %s '
                            '(resolved url %s)' % (info['name'], url))
            else:
                return res.content
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
        根据标识符获得论文的标题
        """
        res = self.sess.get(self.base_url + identifier, verify=False)
        s = self._get_soup(res.content)
        url = 'https:' + s.find('div', attrs={'id': 'link'}).find('a').attrs['href']
        citation = s.find(name='div', attrs={'id': 'citation'}, recursive=True)
        name = citation.find('i').text
        doi = citation.text[citation.text.find('doi:') + 4:-1]
        if not url or not name or not doi:
            logger.error('scihub数据库不存在这篇论文！')
            return None
        return {'name': name, 'doi': doi, 'url': url}

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

    def vaild_name(self, name):
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
            html = requests.get(url=GOOGLE_SCHOLAR_URL + '?hl=zh-CN&q=' + query + '&start=' + str(i),
                                headers={'User-Agent': ScholarConf.USER_AGENT})

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
                response = self.sess.get(base_url, headers={'User-Agent': ScholarConf.USER_AGENT})
                content_type_ = response.headers['Content-Type']
                if content_type_.find('text/html') < 0 and content_type_.find('application') >= 0:
                    logger.info(base_url + '这是一个直接可以下载的链接！')
                    results.append({'base_url': base_url, 'response': response})
                    continue
                info = self.generate_paper_info(base_url)
                if not info:  # 在scihub数据库能查到该论文时
                    info['base_url'] = base_url
                    results.append(info)
                    j += 1
            i += 10
            limit -= j
            time.sleep(0.5)

        return results

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
    DEFAULT_OUTPUT_PATH = r'C:\Users\papers'

    class Channel(Enum):
        GOOGLE_SCHOLAR = 1
        BAIDU_XUESHU = 2
        PUBLONS = 3
        SCIENCE_DIRECT = 4

    def __init__(self) -> None:
        super().__init__()
        self.__outputPath = None
        self.__proxy = None
        self.__downloadChannel = None  # 论文搜索渠道

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

    @property
    def downloadChannel(self):
        return self.__outputPath

    @downloadChannel.setter
    def downloadChannel(self, downloadChannel):
        self.__downloadChannel = downloadChannel


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

    @property
    def dois(self):
        return self.__dois

    @dois.setter
    def dois(self, dois):
        self.__dois = dois

    @property
    def urls(self):
        return self.__urls

    @urls.setter
    def urls(self, urls):
        self.__urls = urls


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