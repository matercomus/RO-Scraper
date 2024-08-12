"""Scraper for Rijksoverheid archive."""

import random
import requests
import time
import json
from datetime import datetime
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
}


def get_root_url(date):
    rand_num = random.randint(0, 999999)
    ROOT_URL = f"https://archief28.sitearchief.nl/archives/sitearchief/{date}{rand_num}/https://www.rijksoverheid.nl"
    return ROOT_URL


def get_response(url):
    response = requests.get(url, headers=HEADERS)
    return response


def parse_publ_date(publ_date):
    return datetime.strptime(publ_date, "%d-%m-%Y | %H:%M")


def extract_news_articles(html):
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.find_all("div", class_="brick")

    news_articles = []
    for article in articles:
        a_tag = article.find("a")
        h3_tag = article.find("h3")
        publ_date_tag = article.find("span", class_="publDate")

        if a_tag and h3_tag and publ_date_tag:
            link = a_tag["href"]
            title = h3_tag.text.strip()
            publ_date = parse_publ_date(publ_date_tag.text.strip())
            news_articles.append({"link": link, "title": title, "publ_date": publ_date})

    return news_articles


def get_article_content(url):
    full_url = get_root_url(date) + url
    response = get_response(full_url)
    print(f"Getting article content from {full_url}")
    print(response.text)
    return response.text


def extract_article_content(html):
    """Extract the content of the article."""
    soup = BeautifulSoup(html, "html.parser")
    content_div = soup.find("div", class_="article content")
    if content_div is None:
        content_div = soup.find("div", id="content", class_="article")
    if content_div:
        return content_div.text.strip()
    else:
        return ""


def save_to_json(news_articles, filename):
    segregated_articles = {}
    for article in news_articles:
        publ_date_str = article["publ_date"].strftime("%Y-%m-%d")
        if publ_date_str not in segregated_articles:
            segregated_articles[publ_date_str] = []
        segregated_articles[publ_date_str].append(article)

    with open(filename, "w") as f:
        json.dump(segregated_articles, f, default=str)


def scrape_and_save_news_articles(date, filename, delay=1):
    root_url = get_root_url(date)
    actuel_url = root_url + "/actueel"
    response = get_response(actuel_url)
    news_articles = extract_news_articles(response.text)

    for article in news_articles:
        time.sleep(delay)
        article_html = get_article_content(article["link"])
        article["full_content"] = extract_article_content(article_html)

    save_to_json(news_articles, filename)


if __name__ == "__main__":
    date = "20180301"
    filename = "news_articles.json"
    scrape_and_save_news_articles(date, filename)
