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


def fetch_by_doi(dois: list, path: str):
    """
    根据 doi 获取文档
    Args:
        dois: 文献DOI号列表
        path: 存储文件夹
    """

    sh = SciHub()
    loop = asyncio.get_event_loop()
    # 获取所有需要下载的scihub直链
    tasks = [sh.async_get_direct_url(doi) for doi in dois]
    all_direct_urls = loop.run_until_complete(asyncio.gather(*tasks))
    print(all_direct_urls)

    # 下载所有论文
    loop.run_until_complete(sh.async_download(loop, all_direct_urls, path=path))
    loop.close()


if __name__ == '__main__':
    # 关键词搜索并下载论文
    # search("quant", 10)

    # 根据doi搜索下载论文
    fetch_by_doi(["10.1088/1751-8113/42/50/504005"], f"files/")
