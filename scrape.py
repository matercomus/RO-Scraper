"""Scraper for Rijksoverheid archive."""

import random
import requests
import time
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import logging

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
}

logging.basicConfig(level=logging.INFO)


def get_root_url(date):
    rand_num = random.randint(0, 999999)
    return f"https://archief28.sitearchief.nl/archives/sitearchief/{date}{rand_num}/https://www.rijksoverheid.nl"


def get_response(url):
    response = requests.get(url, headers=HEADERS)
    logging.info(f"Sent request to {url}, received status code {response.status_code}")
    return response


def parse_publ_date(publ_date):
    formats = ["%d-%m-%Y | %H:%M", "%d-%m-%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(publ_date, fmt)
        except ValueError:
            continue
    raise ValueError(f"Date format not recognized: {publ_date}")


def extract_news_articles(html):
    """Extract news articles' links, titles, and publication dates."""
    soup = BeautifulSoup(html, "html.parser")
    news_articles = []

    articles = soup.find_all("a", class_="news")
    for article in articles:
        link = article["href"]
        title = article.find("h3").text.strip()
        publ_date_tag = article.find("p", class_="meta")
        if publ_date_tag:
            publ_date = parse_publ_date(
                publ_date_tag.text.strip().split("|")[1].strip()
            )
            news_articles.append({"link": link, "title": title, "publ_date": publ_date})

    if not news_articles:
        logging.info("No news block found.")
    return news_articles


def get_article_content(url, date):
    full_url = get_root_url(date) + url
    response = get_response(full_url)
    return response.text


def extract_article_content(html):
    """Extract the content of the article."""
    soup = BeautifulSoup(html, "html.parser")
    content_div = soup.find("div", class_="article content") or soup.find(
        "div", id="content", class_="article"
    )
    return content_div.text.strip() if content_div else ""


def load_existing_articles(filename):
    try:
        with open(filename, "r") as f:
            existing_articles = json.load(f)
            for date, articles in existing_articles.items():
                for article in articles:
                    article["publ_date"] = datetime.strptime(
                        article["publ_date"], "%Y-%m-%d %H:%M:%S"
                    )
    except (FileNotFoundError, json.JSONDecodeError):
        existing_articles = {}
    return existing_articles


def save_to_json(news_articles, filename):
    existing_articles = load_existing_articles(filename)

    for article in news_articles:
        publ_date_str = article["publ_date"].strftime("%Y-%m-%d")
        if publ_date_str not in existing_articles:
            existing_articles[publ_date_str] = []
        existing_articles[publ_date_str].append(article)

    with open(filename, "w") as f:
        json.dump(existing_articles, f, default=str, indent=4)


def get_dates(start_date, end_date):
    """Generate dates from start_date to end_date."""
    current_date = start_date
    while current_date <= end_date:
        yield current_date
        current_date += timedelta(days=1)


def scrape_page(date_str, page, all_articles, delay):
    root_url = get_root_url(date_str)
    actual_url = f"{root_url}/actueel/nieuws?pagina={page}"
    response = get_response(actual_url)
    news_articles = extract_news_articles(response.text)
    time.sleep(delay)

    if not news_articles:
        logging.info(f"No more articles found on page {page}. Stopping pagination.")
        return False

    for article in news_articles:
        if article["link"] not in all_articles:
            time.sleep(delay)
            article_html = get_article_content(article["link"], date_str)
            article["full_content"] = extract_article_content(article_html)
            all_articles[article["link"]] = article
        else:
            logging.info(f"Article {article['link']} already scraped.")

    return True


def scrape_and_save_news_articles(start_date, end_date, delay=1):
    filename = "news_articles.json"
    all_articles = {
        article["link"]: article
        for date_articles in load_existing_articles(filename).values()
        for article in date_articles
    }

    for date in get_dates(start_date, end_date):
        date_str = date.strftime("%Y%m%d")

        for page in range(1, 51):
            if not scrape_page(date_str, page, all_articles, delay):
                break

            save_to_json(list(all_articles.values()), filename)
            logging.info(f"Appended articles to {filename}")


if __name__ == "__main__":
    start_date = datetime(2018, 3, 1)
    end_date = datetime(2018, 3, 31)
    scrape_and_save_news_articles(start_date, end_date)
