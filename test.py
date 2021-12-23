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
