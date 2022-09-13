# -*- coding: utf-8 -*-


class NotExistError(Exception):
    """论文找不到的错误"""


class VerificationError(Exception):
    """搜索时需要验证码"""


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


class ArgumentsError(Exception):
    """参数错误异常"""
