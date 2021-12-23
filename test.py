from scihub import SciHub
import bs4

if __name__ == '__main__':
    soup = bs4.BeautifulSoup(open('./index.html', mode='rt', encoding='utf8'), from_encoding="utf8", features="lxml")


    res_set = soup.find_all(
        lambda tag: tag.name == 'a' and tag.has_attr('id') and tag.has_attr('href')
                    and tag.has_attr('data-clk') and tag.has_attr('data-clk-atid') and tag.attrs['href'].startswith(
            'http'), recursive=True)