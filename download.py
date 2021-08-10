import asyncio
from scihub import SciHub


def search(keywords: str, limit: int):
    """
    搜索相关论文并下载

    Args:
        keywords (str): 关键词
        limit (int): 篇数
    """

    sh = SciHub()
    result = sh.search(keywords, limit=limit)
    print(result)

    loop = asyncio.get_event_loop()
    # 获取所有需要下载的scihub直链
    tasks = [sh.async_get_direct_url(paper["doi"]) for paper in result.get("papers", [])]
    all_direct_urls = loop.run_until_complete(asyncio.gather(*tasks))
    print(all_direct_urls)

    # 下载所有论文
    loop.run_until_complete(sh.async_download(loop, all_direct_urls, path=f"files/"))
    loop.close()


def fetch_by_doi(doi: str):
    """
    根据 doi 获取文档
    Args:
        doi: 文献的DOI号
    """

    sh = SciHub()
    loop = asyncio.get_event_loop()
    # 获取所有需要下载的scihub直链
    tasks = [sh.async_get_direct_url(doi)]
    all_direct_urls = loop.run_until_complete(asyncio.gather(*tasks))
    print(all_direct_urls)

    # 下载所有论文
    loop.run_until_complete(sh.async_download(loop, all_direct_urls, path=f"files/"))
    loop.close()


if __name__ == '__main__':
    # search("quant", 10)
    fetch_by_doi("10.1088/1751-8113/42/50/504005")