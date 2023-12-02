import csv
import datetime
import os

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import pandas as pd

FILENAME = "data.csv"


def requests_retry_session(
    retries=5,
    backoff_factor=1,
    status_forcelist=[401, 402, 403, 500, 502, 504],
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def extract_url(links, platform):
    urls = [l["value"] for l in links if l["code"] == platform]
    return "|".join([u.replace("http://", "https://") for u in urls])


usernames = []
with open("usernames.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        usernames.append(row["username"])

data = []
for username in usernames:
    r = requests_retry_session().get(
        f"https://{os.environ['DOMAIN']}/v2.0/projects/{username}"
    )
    r.raise_for_status()
    current = r.json()

    if current["parameters"]["campaign_type"] != "per_month":
        raise ValueError("Campaign is not per month")

    data.append(
        {
            "date": str(datetime.date.today()),
            "slug": current["slug"],
            "name": current["name"],
            "creator_pseudo": current["creator"]["pseudo"],
            "categories": "|".join([e["name"] for e in current["categories"]]),
            "youtube_url": extract_url(current["links"], "youtube"),
            "twitter_url": extract_url(current["links"], "twitter"),
            "tip_amount": int(current["parameters"]["tipperAmount"]),
            "tip_number": int(current["parameters"]["tipperNumber"]),
        }
    )

with open(FILENAME, "a") as f:
    writer = csv.DictWriter(f, data[0].keys(), lineterminator="\n")
    if f.tell() == 0:
        writer.writeheader()
    writer.writerows(data)

csv = pd.read_csv(FILENAME, parse_dates=["date"])

csv.drop_duplicates(subset=["date", "slug"], keep="last", inplace=True)
csv.sort_values(by=["date", "slug"], inplace=True)

csv.to_csv(FILENAME, index=False)
