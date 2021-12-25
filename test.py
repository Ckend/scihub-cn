import yaml

from scihub import SciHub
import bs4

# -*-encoding=utf-8-*-

# pattern = re.compile(r'.*/.*')
# arg = sys.argv[1]
# setting = None
# if not command_args.inputfile:
#     setting = DownLoadCommandSetting()  # 从命令行参数下载
#     end = len(sys.argv)
#     for i in range(1, len(sys.argv)):
#         if sys.argv[i].startswith('-'):
#             end = i
#             break
#     if arg.startswith('http') or arg.startswith('https'):
#         for i in range(1, end):
#             if not arg.startswith('http') and not arg.startswith('https'):
#                 logger.error('输入的url有误，请重新输入')
#                 return None
#         if end > 2:  # 有多个url参数
#             setting.urls = sys.argv[1:end]
#         else:
#             setting.url = arg
#     elif pattern.match(arg):
#         for i in range(1, end):
#             if not pattern.match(sys.argv[i]):
#                 logger.error('输入的doi有误，请重新输入')
#                 return None
#         if end > 2:  # 有多个个doi参数
#             setting.dois = sys.argv[1:end]
#         else:
#             setting.doi = arg
#     else:
#         if end > 2:
#             setting.words = sys.argv[1:end]

bibtex = """@ARTICLE{Cesar2013,
  author = {Jean César},
  title = {An amazing title},
  year = {2013},
  volume = {12},
  pages = {12--23},
  journal = {Nice Journal},
  abstract = {This is an abstract. This line should be long enough to test
     multilines...},
  comments = {A comment},
  keywords = {keyword1, keyword2}
}
"""
import aiohttp


# https://ieeexplore.ieee.org/ielaam/5/8789751/8763885-aam.pdf
async def main():
    async with aiohttp.ClientSession() as sess:
        async with sess.get('https://sci-hub.se/https://ieeexplore.ieee.org/abstract/document/9146372/') as response:
            html = await response.text()
            print(len(html))


if __name__ == '__main__':
    import asyncio
    while True:
        asyncio.get_event_loop().run_until_complete(main())
