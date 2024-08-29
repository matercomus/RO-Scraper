"""
This scrit uses the opendata API to get all available news articles for a given period.
"""

import requests
import json
import os

from datetime import datetime


def get_url(lms_date, offset, rows):
    return f"https://opendata.rijksoverheid.nl/v1/infotypes/news/lastmodifiedsince/{lms_date}/?output=json&offset={offset}&rows={rows}"


def get_articles(lms_date, max_articles=None, end_date=None):
    filename = "articles.json"
    articles = []

    if os.path.exists(filename):
        with open(filename, "r") as f:
            articles = json.load(f)
            if articles:
                lms_date = max(article["lastmodified"] for article in articles)
                lms_date = datetime.strptime(
                    lms_date, "%Y-%m-%dT%H:%M:%S.%fZ"
                ).strftime("%Y%m%d")

    offset = 0
    rows = 200

    while True:
        url = get_url(lms_date, offset, rows)
        response = requests.get(url)
        new_articles = response.json()

        for article in new_articles:
            if any(a["id"] == article["id"] for a in articles):
                continue
            if end_date and article["lastmodified"] > end_date:
                break

            # Get the full data for the article
            full_data_url = f"https://opendata.rijksoverheid.nl/v1/infotypes/news/{article['id']}?output=json"
            full_data_response = requests.get(full_data_url)
            print(full_data_response)
            full_data = full_data_response.json()

            # Update the article with the full data
            article.update({k: v for k, v in full_data.items() if k not in article})

            articles.append(article)

            if max_articles and len(articles) >= max_articles:
                break

        offset += rows
        if (
            len(new_articles) < rows
            or (end_date and article["lastmodified"] > end_date)
            or (max_articles and len(articles) >= max_articles)
        ):
            break

    with open(filename, "w") as f:
        json.dump(articles, f)


def main():
    get_articles("20180101", end_date="20181231")


if __name__ == "__main__":
    main()
