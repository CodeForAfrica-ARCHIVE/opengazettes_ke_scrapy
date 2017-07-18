# -*- coding: utf-8 -*-
import scrapy

from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError, TCPTimedOutError

from datetime import datetime
from ..items import OpengazettesItem
import romanify
from scrapy import signals
import requests
import json


class GazettesSpider(scrapy.Spider):
    name = "gazettes"
    allowed_domains = ["kenyalaw.org"]

    def start_requests(self):
        # Get the year to be crawled from the arguments
        # The year is passed like this: scrapy crawl gazettes -a year=2017
        # Default to current year if year not passed in
        try:
            year = self.year
        except AttributeError:
            year = datetime.now().strftime('%Y')
        
        url = 'http://kenyalaw.org/kenya_gazette/gazette/year/%s' % \
            (year)
        yield scrapy.Request(url, callback=self.parse, errback=self.errback, dont_filter=True)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(GazettesSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.item_dropped, signal=signals.item_dropped)
        return spider

    def item_dropped(self, item, response, exception, spider):
        spider.logger.info('Spider opened: %s', spider.name)
        webhook_url = 'https://hooks.slack.com/services/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'
        message = item +" Item has been dropped"
        slack_data = {
                    "attachments":
                        [
                            {
                                "author_name": "Code4Africa",
                                "author_icon": "https://codeforafrica.org/img/logos/c4a.png",
                                "color": "danger",
                                "pretext": "[ERROR] New Alert for failing scrapers",
                                "text": message,
                                "fields": [
                                    {
                                        "title": "Spider",
                                        "value": spider.name,
                                        "short": False
                                        },
                                        {
                                        "title": "Failed Item",
                                        "value": item,
                                        "short": False
                                        },
                                        {
                                        "title": "Response",
                                        "value": response,
                                        "short": False
                                        },
                                        {
                                        "title": "Exception",
                                        "value": exception,
                                        "short": False
                                        }
                                    ],
                                "image_url": ":warning:",
                                "footer": "Slack API",
                                "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
                                }
                            ]
                    }

    
    def parse(self, response):
        # Get all rows in the "Weekly Issues" div
        weekly_rows = response.xpath('//*[@id="content"]/div[1]/table/tr')
        # Get all rows in the "Special Issues" div
        special_rows = response.xpath('//*[@id="content"]/div[2]/table/tr')

        no_of_weekly_issues = len(weekly_rows)

        rows = weekly_rows + special_rows
        row_counter = 0
        previous_volume_number = False

        for row in rows:
            # Immediately increment row_counter
            row_counter += 1
            gazette_meta = OpengazettesItem()

            # If we have already gone through all weekly, this is special
            # Otherwise, it is still a weekly issue
            if row_counter > no_of_weekly_issues:
                gazette_meta['special_issue'] = True
            else:
                gazette_meta['special_issue'] = False

            gazette_meta['gazette_link'] = row.xpath(
                'td/a/@href').extract_first()

            if gazette_meta['gazette_link']:
                # Add volume and issue number to metadata from URL
                # Here, we replace l with I to handle human input error
                # BEWARE: This might cause weird behaviour in future
                if not previous_volume_number:
                    gazette_meta['gazette_volume'] = romanify.roman2arabic(
                        row.xpath('td/a/@href')
                        .re(r'(Vol*.*No)|(VoI*.*No)')[0]
                        .replace('Vol', '').replace('VoI', '')
                        .replace('.', '').replace('-', '')
                        .replace(' ', '').replace('l', 'I').replace('No', ''))

                    previous_volume_number = gazette_meta['gazette_volume']
                else:
                    gazette_meta['gazette_volume'] = previous_volume_number

                gazette_meta['gazette_number'] = row.xpath('td/a/@href')\
                    .re(r'No *.*')[0].replace('No', '').replace('.', '')\
                    .replace(' ', '')

                # Add publication date to metadata from table data
                gazette_meta['publication_date'] = datetime.strptime(
                    row.xpath('td/text()')[1].extract(), '%d %B,%Y')

                request = scrapy.Request(gazette_meta['gazette_link'],
                                         callback=self.open_single_gazette)
                request.meta['gazette_meta'] = gazette_meta
                yield request
        

    def errback(self, failure):
        self.logger.error(repr(failure))
        webhook_url = 'https://hooks.slack.com/services/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'
        if failure.check(HttpError):
            # these exceptions come from HttpError spider middleware
            # you can get the non-200 response
            message = "Exceptions from HttpError spider middleware due to non-200 response"
            slack_data = {
                        "attachments":
                            [
                                {
                                    "author_name": "Code4Africa",
                                    "author_icon": "https://codeforafrica.org/img/logos/c4a.png",
                                    "color": "danger",
                                    "pretext": "[ERROR] New Alert for failing scrapers",
                                    "fields": [
                                        {
                                            "title": "HttpError",
                                            "value": message,
                                            "short": False
                                            }
                                        ],
                                    "image_url": ":warning:",
                                    "footer": "Slack API",
                                    "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
                                    }
                                ]
                        }
            response = requests.post(
                webhook_url, data=json.dumps(slack_data),
                headers={'Content-Type': 'application/json'}
            )

            response = failure.value.response
            self.logger.error('HttpError on %s', response.url)

        elif failure.check(DNSLookupError):
            # these exceptions come from DNSLookupError spider middleware
            message = "Exceptions from DNSLookupError spider middleware"
            slack_data = {
                        "attachments":
                            [
                                {
                                    "author_name": "Code4Africa",
                                    "author_icon": "https://codeforafrica.org/img/logos/c4a.png",
                                    "color": "danger",
                                    "pretext": "[ERROR] New Alert for failing scrapers",
                                    "fields": [
                                        {
                                            "title": "DNSLookupError",
                                            "value": message,
                                            "short": False
                                            }
                                        ],
                                    "image_url": ":warning:",
                                    "footer": "Slack API",
                                    "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
                                    }
                                ]
                        }
            response = requests.post(
                webhook_url, data=json.dumps(slack_data),
                headers={'Content-Type': 'application/json'}
            )
            request = failure.request
            self.logger.error('DNSLookupError on %s', request.url)

        elif failure.check(TimeoutError, TCPTimedOutError):
            # these exceptions come from TCPTimeOutError spider middleware
            message = "Exceptions from TCPTimedOutError spider middleware"
            slack_data = {
                        "attachments":
                            [
                                {
                                    "author_name": "Code4Africa",
                                    "author_icon": "https://codeforafrica.org/img/logos/c4a.png",
                                    "color": "danger",
                                    "pretext": "[ERROR] New Alert for failing scrapers",
                                    "fields": [
                                        {
                                            "title": "TimeOutError",
                                            "value": message,
                                            "short": False
                                            }
                                        ],
                                    "image_url": ":warning:",
                                    "footer": "Slack API",
                                    "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
                                    }
                                ]
                        }
            response = requests.post(
                webhook_url, data=json.dumps(slack_data),
                headers={'Content-Type': 'application/json'}
            )
            request = failure.request
            self.logger.error('TimeoutError on %s', request.url)


    # Visit individual gazettes link
    # Find PDF download link
    def open_single_gazette(self, response):
        item = response.meta['gazette_meta']
        item['download_link'] = response.css(
            '.sd a::attr(href)')[1].extract()

        request = scrapy.Request(item['download_link'],
                                 callback=self.download_pdf)
        request.meta['gazette_meta'] = item
        yield request

    # Download PDF gazette using files pipeline
    def download_pdf(self, response):
        item = response.meta['gazette_meta']
        if item['special_issue']:
            gazette_number = item['gazette_number'] + '-special'
        else:
            gazette_number = item['gazette_number']
        # Set PDF filename
        item['filename'] = 'opengazettes-ke-vol-%s-no-%s-dated-%s-%s-%s' % \
            (item['gazette_volume'], gazette_number,
                item['publication_date'].strftime("%d"),
                item['publication_date'].strftime("%B"),
                item['publication_date'].strftime("%Y"))
        item['gazette_title'] = 'Kenya Government '\
            'Gazette Vol.%s No.%s Dated %s %s %s' % \
            (item['gazette_volume'], gazette_number,
                item['publication_date'].strftime("%d"),
                item['publication_date'].strftime("%B"),
                item['publication_date'].strftime("%Y"))
        # Set file URLs to be downloaded by the files pipeline
        item['file_urls'] = [item['download_link']]
        yield item
    