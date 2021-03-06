# -*- coding: utf-8 -*-

# Copyright (c) 2016 Clarence Ho (clarenceho at gmail dot com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import re
from datetime import datetime, timedelta
from lxml import html
import traceback
import json
import urllib
from urllib.parse import urlparse
import pytz

from logger import logger
from fetcher import read_http_page

from .base import BaseSource
from .base import RSSBase


class AppleDaily(BaseSource):
    _base_url = "https://hk.news.appledaily.com"

    def _find_date_id(self, raw_page):
        m_d = re.search(r"Fusion\.deployment\=\"([0-9]+)\"", str(raw_page))

        hk_time = datetime.now(pytz.timezone("Hongkong"))
        if hk_time.hour < 4:
            hk_time = hk_time - timedelta(days=1)
        result_date = hk_time.strftime("%Y%m%d")

        result_d = 0
        if m_d:
            result_d = m_d.group(1)

        return result_date, result_d

    def _get_collection(self, section_id, date_id, d):
        payload_query = {
            "feedOffset": 0,
            "feedQuery": 'taxonomy.primary_section._id:"{}" AND type:story AND editor_note:"{}"'.format(
                section_id, date_id
            ),
            "feedSize": 100,
            "sort": "location:asc",
        }
        payload_query = urllib.parse.quote(json.dumps(payload_query))

        query_url = (
            self._base_url
            + "/pf/api/v3/content/fetch/query-feed?query={}&d={}&_website=hk-appledaily".format(
                payload_query, d
            )
        )
        return read_http_page(query_url)

    def get_id(self):
        return "appledaily"

    def get_desc(self):
        return "蘋果日報(香港)"

    def get_articles(self):
        resultList = []
        sections = [
            ("要聞港聞", "/daily/local", self._base_url + "/daily/local/"),
            ("兩岸", "/daily/china", self._base_url + "/daily/china/"),
            ("國際", "/daily/international", self._base_url + "/daily/international/"),
            ("財經", "/daily/finance", self._base_url + "/daily/finance/"),
            ("娛樂", "/daily/entertainment", self._base_url + "/daily/entertainment/"),
            ("體育", "/daily/sports", self._base_url + "/daily/sports/"),
        ]

        try:
            for (title, section_id, url) in sections:
                # for each section, insert a title...
                resultList.append(self.create_section(title))
                # ... then retrieve the json content
                raw_page = read_http_page(url)
                date_id, d = self._find_date_id(raw_page)
                if date_id and d:
                    raw_result = self._get_collection(section_id, date_id, d)
                    result = json.loads(raw_result)
                    for article in result["content_elements"]:
                        desc = article["headlines"]["basic"]
                        href = article["website_url"]
                        abstract = None
                        if (
                            "content_elements" in article
                            and len(article["content_elements"]) > 1
                            and "content" in article["content_elements"][0]
                        ):
                            abstract = article["content_elements"][0]["content"]
                        if desc and href:
                            resultList.append(
                                self.create_article(
                                    desc.strip(), self._base_url + href, abstract
                                )
                            )

        except Exception as e:
            logger.exception("Problem processing url: " + str(e))
            logger.exception(
                traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
            )

        return resultList


class MingPaoHK(RSSBase):
    def get_id(self):
        return "mingpaohk"

    def get_desc(self):
        return "明報(香港)"

    def get_rss_links(self):
        return [
            ("要聞", "http://news.mingpao.com/rss/pns/s00001.xml"),
            ("港聞", "http://news.mingpao.com/rss/pns/s00002.xml"),
            ("經濟", "http://news.mingpao.com/rss/pns/s00004.xml"),
            ("娛樂", "http://news.mingpao.com/rss/pns/s00016.xml"),
            ("社評‧筆陣", "http://news.mingpao.com/rss/pns/s00003.xml"),
            ("觀點", "http://news.mingpao.com/rss/pns/s00012.xml"),
            ("國際", "http://news.mingpao.com/rss/pns/s00014.xml"),
            ("體育", "http://news.mingpao.com/rss/pns/s00015.xml"),
            ("副刊", "http://news.mingpao.com/rss/pns/s00005.xml"),
            ("深度報道", "http://news.mingpao.com/rss/pns/s00285.xml"),
            ("偵查報道", "http://news.mingpao.com/rss/pns/s00287.xml"),
        ]


class OrientalDailyRSS(RSSBase):
    def get_id(self):
        return "orientaldailyrss"

    def get_desc(self):
        return "東方日報RSS(香港)"

    def get_rss_links(self):
        return [
            ("要聞港聞", "http://orientaldaily.on.cc/rss/news.xml"),
            ("兩岸國際", "http://orientaldaily.on.cc/rss/china_world.xml"),
            ("財經", "http://orientaldaily.on.cc/rss/finance.xml"),
            ("娛樂", "http://orientaldaily.on.cc/rss/entertainment.xml"),
            ("副刊", "http://orientaldaily.on.cc/rss/lifestyle.xml"),
        ]


class OrientalDaily(BaseSource):
    def get_id(self):
        return "orientaldaily"

    def get_desc(self):
        return "東方日報(香港)"

    def get_articles(self):
        # get date first
        dateUrl = "http://orientaldaily.on.cc/"
        theDate = datetime.today().strftime("%Y%m%d")
        try:
            doc = html.document_fromstring(read_http_page(dateUrl))
            for aLink in doc.get_element_by_id("topMenu").xpath(
                'ul[contains(@class, "menuList clear")]/li/a[contains(@class, "news")]'
            ):
                href = aLink.attrib["href"]
                match = re.match(r"\/cnt\/news\/([0-9]{8})\/index\.html", href)
                if match and match.lastindex == 1:
                    theDate = match.group(1)
                else:
                    logger.info("no date found. using system date: " + theDate)
        except Exception as e:
            logger.exception("Problem getting date: " + str(e))
            logger.exception(
                traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
            )

        resultList = []
        baseUrl = dateUrl

        sections = [
            ("要聞港聞", "http://orientaldaily.on.cc/cnt/news/" + theDate + "/index.html"),
            (
                "兩岸國際",
                "http://orientaldaily.on.cc/cnt/china_world/" + theDate + "/index.html",
            ),
            ("財經", "http://orientaldaily.on.cc/cnt/finance/" + theDate + "/index.html"),
            (
                "娛樂",
                "http://orientaldaily.on.cc/cnt/entertainment/"
                + theDate
                + "/index.html",
            ),
        ]

        try:
            for (title, url) in sections:
                # for each section, insert a title...
                resultList.append(self.create_section(title))
                # ... then parse the page and extract article links
                doc = html.document_fromstring(read_http_page(url))
                if doc is not None and doc.get_element_by_id("articleList") is not None:
                    for topic in doc.get_element_by_id("articleList").xpath(
                        'ul[contains(@class, "commonBigList")]/li/a'
                    ):
                        if topic.text and topic.get("href"):
                            resultList.append(
                                self.create_article(
                                    topic.text.strip(), baseUrl + topic.get("href")
                                )
                            )

        except Exception as e:
            logger.exception("Problem processing url: " + str(e))
            logger.exception(
                traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
            )

        return resultList


class SingPao(BaseSource):
    def get_id(self):
        return "singpao"

    def get_desc(self):
        return "香港成報"

    def get_articles(self):
        maxPagePerSection = 10
        resultList = []

        sections = [
            ("要聞港聞", "http://www.singpao.com.hk/index.php?fi=news1"),
            ("兩岸國際", "http://www.singpao.com.hk/index.php?fi=news8"),
            ("財經", "http://www.singpao.com.hk/index.php?fi=news3"),
            ("娛樂", "http://www.singpao.com.hk/index.php?fi=news4"),
            ("體育", "http://www.singpao.com.hk/index.php?fi=news5"),
            ("副刊", "http://www.singpao.com.hk/index.php?fi=news7"),
        ]
        baseUrl = "http://www.singpao.com.hk/"

        try:
            for (title, url) in sections:
                # for each section, insert a title...
                resultList.append(self.create_section(title))
                # ... then parse the page and extract article links
                page = 1
                maxPage = 1
                while page <= maxPage and page <= maxPagePerSection:
                    doc = html.document_fromstring(
                        read_http_page(url + "&page=" + str(page))
                    )
                    page += 1

                    for topic in doc.xpath('//td/a[contains(@class, "list_title")]'):
                        if topic.text and topic.get("href"):
                            resultList.append(
                                self.create_article(
                                    topic.text.strip(), baseUrl + topic.get("href")
                                )
                            )

                    for pageIndex in doc.xpath(
                        '//a[contains(@class, "fpagelist_css")]'
                    ):
                        if pageIndex.text is not None:
                            match = re.match(r"^([0-9]+)$", pageIndex.text.strip())
                            if (
                                match
                                and match.lastindex == 1
                                and int(match.group(1)) > maxPage
                            ):
                                maxPage = int(match.group(1))

        except Exception as e:
            logger.exception("Problem processing url: " + str(e))
            logger.exception(
                traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
            )

        return resultList


class HeadlineDaily(RSSBase):
    def get_id(self):
        return "stheadline"

    def get_desc(self):
        return "頭條日報"

    def get_rss_links(self):
        return [
            ("頭條日報", "http://hd.stheadline.com/rss/news/daily/"),
        ]


class TaKungPao(BaseSource):
    def get_id(self):
        return "takungpao"

    def get_desc(self):
        return "大公網"

    def get_articles(self):
        resultList = []

        sections = [
            ("港聞", "http://www.takungpao.com.hk/hongkong/"),
            ("內地", "http://www.takungpao.com.hk/mainland/"),
            ("台灣", "http://www.takungpao.com.hk/taiwan/"),
            ("國際", "http://www.takungpao.com.hk/international/"),
            ("評論", "http://www.takungpao.com.hk/opinion/"),
            ("經濟", "http://www.takungpao.com.hk/finance/"),
            ("文化", "http://www.takungpao.com.hk/culture/"),
            ("體育", "http://www.takungpao.com.hk/sports/"),
            ("娛樂", "http://www.takungpao.com.hk/ent/"),
        ]

        try:
            for (title, url) in sections:
                # for each section, insert a title...
                resultList.append(self.create_section(title))
                # ... then parse the page and extract article links
                doc = html.document_fromstring(read_http_page(url))

                for topic in doc.xpath(
                    '//div[contains(@class, "list_tuwen")]/div[contains(@class, "content")]'
                ):
                    title = topic.xpath('ul/li[contains(@class, "title")]/a')
                    intro = topic.xpath('ul/li[contains(@class, "intro")]/a')

                    if title and title[0].text and title[0].get("href"):
                        resultList.append(
                            self.create_article(
                                title[0].text.strip(),
                                title[0].get("href"),
                                intro[0].text.strip()
                                if intro and intro[0].text
                                else None,
                            )
                        )

        except Exception as e:
            logger.exception("Problem processing url: " + str(e))
            logger.exception(
                traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
            )

        return resultList


class Scmp(RSSBase):
    def get_id(self):
        return "scmp"

    def get_desc(self):
        return "South China Morning Post"

    def get_rss_links(self):
        return [
            ("News", "https://www.scmp.com/rss/91/feed"),
            ("Business", "https://www.scmp.com/rss/92/feed"),
            ("Tech", "https://www.scmp.com/rss/36/feed"),
            ("Life", "https://www.scmp.com/rss/94/feed"),
            ("Culture", "https://www.scmp.com/rss/322296/feed"),
            ("Sport", "https://www.scmp.com/rss/95/feed"),
        ]


class Etnet(RSSBase):
    def get_id(self):
        return "etnet"

    def get_desc(self):
        return "經濟通"

    def get_rss_links(self):
        return [
            ("精選新聞", "http://www.etnet.com.hk/www/tc/news/rss.php?section=editor"),
            ("焦點專題", "http://www.etnet.com.hk/www/tc/news/rss.php?section=special"),
            ("股市傳聞 	", "http://www.etnet.com.hk/www/tc/news/rss.php?section=rumour"),
            ("股票評論", "http://www.etnet.com.hk/www/tc/news/rss.php?section=commentary"),
        ]


class HkEt(BaseSource):
    def _is_absolute(self, url):
        return bool(urlparse(url).netloc)

    def get_id(self):
        return "hket"

    def get_desc(self):
        return "香港經濟日報"

    def get_articles(self):
        resultList = []
        sections = [
            ("金融經濟", "https://inews.hket.com", "/sran009/金融經濟", 3),
            ("理財", "https://wealth.hket.com", "/", 1),
            ("科技", "https://inews.hket.com", "/sran010/科技", 2),
            ("中國", "https://china.hket.com", "/", 1),
            ("國際", "https://inews.hket.com", "/sran011/國際", 2),
            ("商業", "https://inews.hket.com", "/sran012/商業", 2),
        ]
        seen_url = {}

        try:
            for (title, base_url, url, pages) in sections:
                # for each section, insert a title...
                resultList.append(self.create_section(title))
                # ... then get page and parse
                for page in range(1, pages + 1):
                    doc = html.document_fromstring(
                        read_http_page(base_url + url + "?p={}".format(page))
                    )
                    for topic in doc.xpath(
                        '//div[contains(@class, "listing-widget-33") or contains(@class, "listing-widget-4") or contains(@class, "listing-widget-9")]/a[contains(@class, "listing-overlay")]'
                    ):
                        if topic.text and topic.get("href"):
                            topic_url = (
                                topic.get("href")
                                if self._is_absolute(topic.get("href"))
                                else base_url + topic.get("href")
                            )
                            if topic_url not in seen_url:
                                seen_url[topic_url] = None
                                resultList.append(
                                    self.create_article(topic.text.strip(), topic_url)
                                )

        except Exception as e:
            logger.exception("Problem processing url: " + str(e))
            logger.exception(
                traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)
            )

        return resultList
