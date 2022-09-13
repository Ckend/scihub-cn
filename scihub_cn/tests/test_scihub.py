# -*- coding: utf-8 -*-

from scihub_cn.models import PaperInfo
from scihub_cn.scihub import SciHub


def test_api_with_proxy():
    """测试api下载功能"""
    https_proxy = "socks5h://127.0.0.1:10808"
    sh = SciHub(proxy=https_proxy)

    result = sh.download({"doi": '10.1109/ACC.1999.786344'}, is_translate_title=True)
    print(f"论文下载: {result}")
    assert type(result) is PaperInfo


def test_api_without_proxy():
    """测试api下载功能"""
    sh = SciHub()
    result = sh.download(
        info={
            'scihub_url': "https://sci-hub.se/10.1016/j.apsb.2021.06.014"
        }, is_translate_title=True
    )
    print(f"论文下载: {result}")
    assert type(result) is PaperInfo
