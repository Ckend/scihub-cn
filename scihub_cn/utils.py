# -*- coding: utf-8 -*-
import hashlib
import json
import random
import re
import time
from typing import Optional

import requests

from scihub_cn.models import PaperDetailDescription


def translate(content: str, proxy=None) -> str:
    """对文本content进行翻译"""
    lts = str(int(time.time() * 1000))
    salt = lts + str(random.randint(0, 9))
    sign_str = 'fanyideskweb' + content + salt + 'Ygy_4c=r#e#4EX^NUGUc5'
    m = hashlib.md5()
    m.update(sign_str.encode())
    sign = m.hexdigest()
    url = 'https://fanyi.youdao.com/translate_o?smartresult=dict&smartresult=rule'
    headers = {
        "Referer": "https://fanyi.youdao.com/",
        "Cookie": 'OUTFOX_SEARCH_USER_ID=-1124603977@10.108.162.139; JSESSIONID=aaamH0NjhkDAeAV9d28-x; OUTFOX_SEARCH_USER_ID_NCOO=1827884489.6445506; fanyi-ad-id=305426; fanyi-ad-closed=1; ___rl__test__cookies=1649216072438',
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36"
    }
    data = {
        "i": content,
        "from": "AUTO",
        "to": "AUTO",
        "smartresult": "dict",
        "client": "fanyideskweb",
        "salt": salt,
        "sign": sign,
        "lts": lts,
        "bv": "a0d7903aeead729d96af5ac89c04d48e",
        "doctype": "json",
        "version": "2.1",
        "keyfrom": "fanyi.web",
        "action": "FY_BY_REALTlME",
    }
    res = requests.post(url, headers=headers, data=data, proxies=proxy)
    response = json.loads(res.text)
    value = response['translateResult'][0][0]['tgt']
    return value.replace(" ", "").replace("。", "")


def split_description(content: str) -> Optional[PaperDetailDescription]:
    """将抓取的转换成"""
    # description: authors, title, publisher, doi
    # test case1: {"doi": '10.1109/ACC.1999.786344'}, 无authors
    # test case2: {"doi": "10.1016/j.biopha.2019.109317"} authors, title, publisher, doi齐全
    pattern = re.compile(
        r"^(?P<authors>(?:.*?, )+\w+\. \(\d+\)\. )?(?P<title>[A-Z].*?\. )(?P<publisher>[A-Z].*?\. )(?P<doi>(?:doi:|https:).*?)$")

    res = re.search(pattern, content)
    if res:
        return PaperDetailDescription(
            authors=res.group("authors"),
            # 去掉末尾的字符
            title=res.group("title").strip(". "),
            publisher=res.group("publisher"),
            doi=res.group("doi")
        )
    else:
        return None


if __name__ == '__main__':
    http_proxy = "socks5h://127.0.0.1:10808"
    https_proxy = "socks5h://127.0.0.1:10808"
    proxies = {
        "https": https_proxy,
        "http": http_proxy
    }
    translated_str = translate("你好", proxy=proxies)
    print(translated_str)

