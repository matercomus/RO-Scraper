"""Scraper for Rijksoverheid archive."""

import random
import requests
import time
import json
from datetime import datetime
from bs4 import BeautifulSoup
from datetime import timedelta
import logging

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
}


logging.basicConfig(level=logging.INFO)


def get_root_url(date):
    rand_num = random.randint(0, 999999)
    ROOT_URL = f"https://archief28.sitearchief.nl/archives/sitearchief/{date}{rand_num}/https://www.rijksoverheid.nl"
    return ROOT_URL


def get_response(url):
    response = requests.get(url, headers=HEADERS)
    logging.info(f"Sent request to {url}, received status code {response.status_code}")
    logging.info(f"Response text: {response.text}")
    return response


def parse_publ_date(publ_date):
    return datetime.strptime(publ_date, "%d-%m-%Y | %H:%M")


def extract_news_articles(html, date):
    """Extract news articles' links, titles, and publication dates."""
    soup = BeautifulSoup(html, "html.parser")
    news_block = soup.find("div", class_="block news")
    if not news_block:
        logging.info("No news block found.")
        return []

    articles = news_block.find_all("div", class_="headline")
    articles += news_block.find_all("div", class_="regular")
    articles += news_block.find_all("div", class_="regular odd")

    news_articles = []
    for article in articles:
        a_tag = article.find("a")
        h3_tag = article.find("h3")
        publ_date_tag = article.find("p", class_="meta")

        if a_tag and h3_tag and publ_date_tag:
            link = a_tag["href"].replace(get_root_url(date), "")
            title = h3_tag.text.strip()
            publ_date = parse_publ_date(publ_date_tag.text.strip())
            news_articles.append({"link": link, "title": title, "publ_date": publ_date})

    return news_articles


def get_article_content(url, date):
    full_url = get_root_url(date) + url
    response = get_response(full_url)
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


def get_dates(start_date, end_date):
    """Generate dates from start_date to end_date."""
    current_date = start_date
    while current_date <= end_date:
        yield current_date
        current_date += timedelta(days=1)


def scrape_and_save_news_articles(start_date, end_date, delay=1):
    all_articles = {}
    for date in get_dates(start_date, end_date):
        date_str = date.strftime("%Y%m%d")
        root_url = get_root_url(date_str)
        actuel_url = root_url + "/actueel"
        response = get_response(actuel_url)
        news_articles = extract_news_articles(response.text, date_str)
        time.sleep(delay)

        for article in news_articles:
            if article["link"] not in all_articles:
                time.sleep(delay)
                article_html = get_article_content(article["link"], date_str)
                article["full_content"] = extract_article_content(article_html)
                all_articles[article["link"]] = article
            else:
                logging.info(f"Article {article['link']} already scraped.")

    filename = f"news_articles_{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}.json"
    save_to_json(list(all_articles.values()), filename)


if __name__ == "__main__":
    start_date = datetime(2016, 3, 29)
    end_date = datetime(2016, 3, 31)
    scrape_and_save_news_articles(start_date, end_date)
