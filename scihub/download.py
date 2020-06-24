from scihub import SciHub

sh = SciHub()

# 搜索词
keywords = "Dragon Boat Festival"

# 搜索该关键词相关的论文，limit为篇数
result = sh.search(keywords, limit=10)

print(result)

for index, paper in enumerate(result.get("papers", [])):
    # 批量下载这些论文
    sh.download(paper["url"], path=f"files/{keywords.replace(' ', '_')}_{index}.pdf")
