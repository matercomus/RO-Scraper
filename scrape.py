import random
import requests
import time
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import logging
import argparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
}

logging.basicConfig(level=logging.INFO)


def get_root_url(date):
    rand_num = random.randint(0, 999999)
    return f"https://archief28.sitearchief.nl/archives/sitearchief/{date}{rand_num}/https://www.rijksoverheid.nl"


def get_response(url):
    response = requests.get(url, headers=HEADERS)
    logging.debug(f"Sent request to {url}, received status code {response.status_code}")
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
            for _, articles in existing_articles.items():
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

    logging.info(f"Saved articles to {filename}.")


def get_dates(start_date, end_date):
    """Generate dates from start_date to end_date."""
    current_date = start_date
    while current_date <= end_date:
        yield current_date
        current_date += timedelta(days=1)


def scrape_page(
    date_str, page, all_articles, delay, start_date, end_date, no_articles_counter
):
    root_url = get_root_url(date_str)
    actual_url = f"{root_url}/actueel/nieuws?pagina={page}"
    response = get_response(actual_url)
    news_articles = extract_news_articles(response.text)
    time.sleep(delay)

    if not news_articles:
        logging.info(f"No more articles found on page {page}. Stopping pagination.")
        return False, no_articles_counter

    articles_in_range = False
    for article in news_articles:
        if start_date <= article["publ_date"] <= end_date:
            articles_in_range = True
            if article["link"] not in all_articles:
                time.sleep(delay)
                article_html = get_article_content(article["link"], date_str)
                article["full_content"] = extract_article_content(article_html)
                all_articles[article["link"]] = article
            else:
                logging.debug(f"Skipping already scraped article: {article['link']}")

    if not articles_in_range:
        no_articles_counter += 1
    else:
        no_articles_counter = 0

    return True, no_articles_counter


def scrape_and_save_news_articles(
    start_date, end_date, delay=1, no_article_skip_threashold=3, filename=None
):
    if filename is None:
        filename = "news_articles_between_{start_date}_and_{end_date}.json".format(
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
        )
    all_articles = {
        article["link"]: article
        for date_articles in load_existing_articles(filename).values()
        for article in date_articles
    }

    no_articles_counter = 0

    for date in get_dates(start_date, end_date):
        date_str = date.strftime("%Y%m%d")
        no_articles_counter = 0  # Reset counter for each new date
        for page in range(1, 51):
            logging.info(f"Scraping page {page} for date {date_str}.")
            continue_scraping, no_articles_counter = scrape_page(
                date_str,
                page,
                all_articles,
                delay,
                start_date,
                end_date,
                no_articles_counter,
            )
            if (
                not continue_scraping
                or no_articles_counter >= no_article_skip_threashold
            ):
                logging.info(
                    f"Stopping pagination for date {date_str} due to {no_article_skip_threashold} consecutive pages with no articles in date range."
                )
                break  # Break out of the pagination loop, but continue to the next date

        save_to_json(list(all_articles.values()), filename)

    logging.info(f"Finished scraping news articles from {start_date} to {end_date}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape and save news articles.")
    parser.add_argument(
        "start_date",
        type=lambda d: datetime.strptime(d, "%Y-%m-%d"),
        help="Start date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "end_date",
        type=lambda d: datetime.strptime(d, "%Y-%m-%d"),
        help="End date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--delay", type=float, default=1, help="Delay between requests in seconds"
    )
    parser.add_argument(
        "--no_article_skip_threashold",
        type=int,
        default=3,
        help="Number of consecutive pages with no articles to skip pagination",
    )
    parser.add_argument(
        "--filename", type=str, default=None, help="Filename to save the articles"
    )

    args = parser.parse_args()

    scrape_and_save_news_articles(
        args.start_date,
        args.end_date,
        delay=args.delay,
        no_article_skip_threashold=args.no_article_skip_threashold,
        filename=args.filename,
    )
