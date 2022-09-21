# -*- coding: utf-8 -*-
from scihub_cn.utils import split_description, translate


def test_split_description():
    # content = "Clément, J.-L., Pesenti, S., Ilharreborde, B., Morin, C., Charles, Y.-P., Parent, H.-F., … Solla,
    # F. (2021). Proximal junctional kyphosis is a rebalancing spinal phenomenon due to insufficient postoperative
    # thoracic kyphosis after adolescent idiopathic scoliosis surgery. European Spine Journal, 30(7), 1988–1997.
    # doi:10.1007/s00586-021-06875-4 "
    content = "Wang, X., Sun, K., Gu, S., Zhang, Y., Wu, D., Zhou, X., … Ding, Y. (2021). Construction of a novel " \
              "electron transfer pathway by modifying ZnIn2S4 with α-MnO2 and Ag for promoting solar H2 generation. " \
              "Applied Surface Science, 549, 149341. doi:10.1016/j.apsusc.2021.149341 "
    res = split_description(content)
    assert res is not None and res.doi


def test_translate():
    http_proxy = "socks5h://127.0.0.1:10808"
    https_proxy = "socks5h://127.0.0.1:10808"
    proxies = {
        "https": https_proxy,
        "http": http_proxy
    }
    translated_str = translate("你好", proxy=proxies)
    print(translated_str)
    assert translated_str is "hello"
