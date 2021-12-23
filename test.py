from scihub import SciHub
import bs4

# -*-encoding=utf-8-*-
import numpy as np

# 第二类斯特林数
'''
n个元素的集合划分为正好k个非空子集的方法的数目
递推公式为： 　　S(n,k)=0; (n<k||k=0) 　　S(n,n) = S(n,1) = 1, 　　
S(n,k) = S(n-1,k-1) + kS(n-1,k).
'''


def S(n, m):
    if m > n or m == 0:
        return 0
    if n == m:
        return 1
    if m == 1:
        return 1
    return S(n - 1, m - 1) + S(n - 1, m) * m


def total(n):
    sumtotal = 0
    for i in np.arange(0, n + 1, 1):
        sumtotal = sumtotal + S(n, i)
    return sumtotal


print(S(9, 6) * 720)

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