# Open Gazettes KE Scraper

[Kenya Law](http://kenyalaw.org/kenya_gazette/gazette) gazette scraper built on [Scrapy](https://scrapy.org)

## Installation
- Clone repo and cd into it
- Make virtual env
- cd opengazettes
- pip install -r requirements.txt
- set ENV variables
    - `SCRAPY_AWS_ACCESS_KEY_ID` - Get this from AWS
    - `SCARPY_AWS_SECRET_ACCESS_KEY` - Get this from AWS
    - `SCRAPY_FEED_URI=s3://name-of-bucket-here/gazettes/data.jsonlines` - Where you want the `jsonlines` output for crawls to be saved. This can also be a local location.
    - `SCRAPY_FILES_STORE=s3://name-of-bucket-here/gazettes` - Where you want scraped gazettes to be stored. This can also be a local location.


## Deploying to [Scraping Hub](https://scrapinghub.com)

It is recommended that you deploy your crawler to scrapinghub for easy management. Follow these steps to do this:

- Sign up for free scraping hub account [here](https://app.scrapinghub.com)
- Install shub locally using `pip install shub`. Further instructions [here](https://shub.readthedocs.io/en/stable/quickstart.html#installation)
- `shub login`
- `shub deploy`
