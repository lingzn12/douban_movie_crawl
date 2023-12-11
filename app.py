import json
import re
import time as tm
from typing import List, Tuple

import requests as rt
from lxml import etree
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.common.by import By


class Movie(BaseModel):
    name: str
    image_url: str
    url: str
    director: str
    scriptwriter: str
    leading_role: str
    genre: str
    production_country: str
    language: str
    release_date: str
    duration: str
    alias: str
    movie_intro: str
    actor_info: List[Tuple[str, str]]
    douban_score: dict


def get_html_data(url: str, header=None):
    if header is None:
        header = {
            "Cookie": "__utmc=223695111;__utmz=30149280.1702258585.1.1.utmcsr=cn.bing.com|utmccn=("
                      "referral)|utmcmd=referral|utmcct=/;_pk_id.100001.4cf6=0bdf05407e594882.1702259655.;bid=oSRcg3B"
                      "-v5U"
                      ";__utmb=223695111.0.10.1702259655;__utma=30149280.644161280.1702258585.1702258585.1702258585.1"
                      ";_pk_ref"
                      ".100001.4cf6=%5B%22%22%2C%22%22%2C1702259655%2C%22https%3A%2F%2Fwww.douban.com%2F%22%5D;__utmb"
                      "=30149280.2.10.1702258585;__utmc=30149280;_vwo_uuid_v2=D7393D14CE18941BF738EA73DC8EF8C28"
                      "|e17da6cddc4509aa9a52e61e28013e87;__utma=223695111.835299369.1702259655.1702259655.1702259655"
                      ".1;__utmz"
                      "=223695111.1702259655.1.1.utmcsr=douban.com|utmccn=("
                      "referral)|utmcmd=referral|utmcct=/;__yadk_uid=Ax4raWL6DkY5j2ZPj3RvFUiBfU3SLPFI;_pk_ses.100001"
                      ".4cf6=1"
                      ";ap_v=0,6.0;ll='118281'",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/92.0.4515.107 Safari/537.36 Edg/92.0.902.55",
        }

    r = rt.get(url, headers=header).text
    return r


def xpath(html_text: str, xpath_str: str):
    tree = etree.HTML(html_text)
    elements = tree.xpath(xpath_str)
    return elements


def write_json(write_data: dict, filepath: str, encoding: str = "utf_8") -> None:
    """
    创建json文件函数
    @param write_data: 写入数据
    @param filepath: 保存地址
    @param encoding: 文件编码
    @return: None
    """
    with open(filepath, "w", encoding=encoding) as f:
        json.dump(write_data, f, indent=4, ensure_ascii=False)


time1 = tm.time()


def save_movie_info(file_name: str, xpath_str: str = None, url: str = None, movie_url_list: list = None):
    get_movie_result_list = {}

    # 获取电影信息
    if xpath_str is not None and movie_url_list is None and url is not None:
        rt_movie_douban = get_html_data(url)
        movie_url_list = list(set([i.get("href") for i in xpath(rt_movie_douban, xpath_str)]))

    for movie_url in movie_url_list:
        movie_data = get_html_data(movie_url)

        if (not xpath(movie_data, "//*[@id='celebrities']") or
                not xpath(movie_data, "//*[@id='info']/span[1]/span[2]/a/text()")):
            continue

        movie_name = xpath(movie_data, "//*[@id='content']/h1/span/text()")
        info_span_text = xpath(movie_data, "//*[@id='info']/span/text()")
        info_text = xpath(movie_data, "//*[@id='info']/text()")

        type_result = info_span_text[
                      info_span_text.index("类型:") + 1: min(
                          i
                          for i in [
                              info_span_text.index("制片国家/地区:")
                              if "制片国家/地区:" in info_span_text
                              else float("inf"),
                              info_span_text.index("官方网站:")
                              if "官方网站:" in info_span_text
                              else float("inf"),
                          ]
                      )
                      ]
        info_text_list = [
            i.replace(" ", "")
            for i in info_text
            if i != "\n        " and i != " " and i != "\n        \n        " and i != " / "
        ]

        start = next(
            i for i, s in enumerate(info_span_text) if re.match(r"\d{4}-\d{2}-\d{2}\(.*\)", s)
        )

        dates, other_info = (
            info_span_text[start: next(
                i + start
                for i, s in enumerate(info_span_text[start:])
                if not re.match(r"\d{4}-\d{2}-\d{2}\(.*\)", s)
            )
            ],
            info_span_text[next(
                i + start
                for i, s in enumerate(info_span_text[start:])
                if not re.match(r"\d{4}-\d{2}-\d{2}\(.*\)", s)
            ):
            ],
        )

        # 获取演员信息
        actor_data = xpath(movie_data, "//*[@id='celebrities']/ul/li/a/div/@style")
        actor_intro_combined = [f'{name}/{role}' for name, role in
                                zip(xpath(movie_data, "//*[@id='celebrities']/ul/li/div/span/a/text()"),
                                    xpath(movie_data, "//*[@id='celebrities']/ul/li/div/span/text()")
                                    )]

        actor_img_url_result_list = []

        for i in actor_data:
            result = re.findall(r'https://img\d+\.doubanio\.com/view/.+?\.jpg', i)
            if result:
                actor_img_url_result_list.append(result[0])
            else:
                actor_img_url_result_list.append(
                    "https://img1.doubanio.com/f/movie/8dd0c794499fe925ae2ae89ee30cd225750457b4/pics/movie/celebrity"
                    "-default-medium.png"
                )

        actor_intro_result = [(actor, img_url) for actor, img_url in zip(actor_intro_combined,
                                                                         actor_img_url_result_list)]

        name = f"{movie_name[0]}{movie_name[1]}"

        # 豆瓣评分
        total_score = xpath(movie_data, "//*[@id='interest_sectl']/div[1]/div[2]/strong/text()")
        rating_rate = xpath(movie_data, "//*[@id='interest_sectl']/div[1]/div[3]/div/span[2]/text()")

        if total_score or rating_rate:
            total_score = total_score[0]
            rating_rate = rating_rate[::-1]
        else:
            total_score = 0
            rating_rate = [0, 0, 0, 0, 0]

        # 构建Movie对象
        movie = Movie(
            name=name,
            image_url=xpath(movie_data, "//*[@id='mainpic']/a/img")[0].get("src"),
            url=movie_url_list[0],
            director=xpath(movie_data, "//*[@id='info']/span[1]/span[2]/a/text()")[0],
            scriptwriter="/".join(
                xpath(movie_data, "//*[@id='info']/span[2]/span[2]/a/text()")
            ),
            leading_role="/".join(
                xpath(movie_data, "//*[@id='info']/span[3]/span[2][@class='attrs']/a/text()")
            ),
            genre="/".join(type_result),
            production_country=info_text_list[0],
            language=info_text_list[1],
            release_date="/".join(dates),
            duration=other_info[1],
            alias=info_text_list[2],
            movie_intro=xpath(movie_data, "//*[@id='link-report-intra']/span/text()")[0],
            actor_info=actor_intro_result,
            douban_score={
                "total_score": total_score,
                "rating_rate": rating_rate
            }
        )

        get_movie_result_list.update({
            name: movie.dict()
        })

    write_json(get_movie_result_list, file_name)


# 热映电影
print("热映电影爬取中...")
save_movie_info(file_name="热映.json", xpath_str="//*[@id='screening']/div[2]/ul/li/ul/li/a ",
                url="https://movie.douban.com/")

# 最近热门电影
print("最近热门电影爬取中...")
driver = webdriver.Edge()
driver.get('https://movie.douban.com/')

# 等待JavaScript渲染
driver.implicitly_wait(5)

element = driver.find_elements(By.XPATH, '//*[@id="content"]/div/div[2]/div[3]/div[3]/div/div[1]/div/div/a')

# 对元素进行操作
save_movie_info(movie_url_list=[ele.get_attribute('href') for ele in element], file_name="热门.json")

driver.quit()

# 排行榜电影
print("排行榜电影爬取中...")
driver = webdriver.Edge()
driver.get('https://movie.douban.com/chart')

# 等待JavaScript渲染
driver.implicitly_wait(5)

element = driver.find_elements(By.XPATH, '//*[@id="content"]/div/div[1]/div/div/table/tbody/tr/td/div/a')

# 对元素进行操作
save_movie_info(movie_url_list=[ele.get_attribute('href') for ele in element], file_name="排行.json")

driver.quit()
time2 = tm.time()
print(f'用时:{time2 - time1}秒')
print("爬取完毕")
