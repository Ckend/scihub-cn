# -*- coding: utf-8 -*-

"""
Sci-API Unofficial API
[Search|Download] research papers from [scholar.google.com|sci-hub.io].

@author zaytoun
@updated by Python实用宝典
"""

import re
import asyncio
import hashlib
import logging
import os
import json
import aiohttp
import requests
from bs4 import BeautifulSoup

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
            dois = [doi.text.replace("DOI：", "").replace("ISBN：", "").strip() for doi in s.find_all('div', class_='doi_wr')]
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

    def download(self, identifier, destination='', path=None):
        """
        Downloads a paper from sci-hub given an indentifier (DOI, PMID, URL).
        Currently, this can potentially be blocked by a captcha if a certain
        limit has been reached.
        """
        data = self.fetch(identifier)
        if not data:
            return
        if not 'err' in data:
            self._save(data['pdf'],
                       os.path.join(destination, path if path else data['name']))

        return data

    def fetch(self, identifier):
        """
        Fetches the paper by first retrieving the direct link to the pdf.
        If the indentifier is a DOI, PMID, or URL pay-wall, then use Sci-Hub
        to access and download paper. Otherwise, just download paper directly.
        """

        try:
            url = self._get_direct_url(identifier)

            # verify=False is dangerous but sci-hub.io 
            # requires intermediate certificates to verify
            # and requests doesn't know how to download them.
            # as a hacky fix, you can add them to your store
            # and verifying would work. will fix this later.
            res = self.sess.get(url, verify=False)

            if res.headers['Content-Type'] != 'application/pdf':
                self._change_base_url()
                logger.info('由于验证码问题，获取 pdf 失败 identifier: %s '
                                           '(resolved url %s)' % (identifier, url))
            else:
                return {
                    'pdf': res.content,
                    'url': url,
                    'name': self._generate_name(res)
                }

        except requests.exceptions.ConnectionError:
            logger.info('Cannot access {}, changing url'.format(self.available_base_url_list[0]))
            self._change_base_url()

        except requests.exceptions.RequestException as e:
            logger.info('由于请求失败，获取pdf失败 %s (resolved url %s).'
                       % (identifier, url))
            return {
                'err': '由于请求失败，获取pdf失败 %s (resolved url %s).'
                       % (identifier, url)
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

    def _generate_name(self, res):
        """
        Generate unique filename for paper. Returns a name by calcuating 
        md5 hash of file contents, then appending the last 20 characters
        of the url which typically provides a good paper identifier.
        """
        name = res.url.split('/')[-1]
        name = re.sub('#view=(.+)', '', name)
        pdf_hash = hashlib.md5(res.content).hexdigest()
        return '%s-%s' % (pdf_hash, name[-20:])

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
