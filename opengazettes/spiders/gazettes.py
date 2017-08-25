# -*- coding: utf-8 -*-
import os
import scrapy

from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError, TCPTimedOutError

from datetime import datetime
import time
import getpass
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
        return spider


    def parse(self, response):
        # try:
        # Get all rows in the "Weekly Issues" div
        weekly_issue_div = '//*[@id="content"]/div[1]/table/tr'
        special_rows_div = '//*[@id="content"]/div[2]/table/tr'

        weekly_rows = response.xpath(weekly_issue_div)
        # Get all rows in the "Special Issues" div
        special_rows = response.xpath(special_rows_div)

        no_of_weekly_issues = len(weekly_rows)
        if special_rows == 0 or no_of_weekly_issues == 0:
            error_name = "PAGE STRUCTURE ERROR"
            message = "Spider failure caused by error on current page structures."\
                       + "\n Weekly issue as %s \n Special issue as %s" % \
                       (weekly_issue_div, special_rows_div)
            self.notification(error_name, message)

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


    def domains(self):
        for domain in self.allowed_domains:
            return domain
    

    def notification(self, error_name, message):
        webhook_url = os.getenv('WEB_HOOK')
        webhook_url = 'https://hooks.slack.com/services/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'
        slack_data = {
                        "attachments":
                            [
                                {
                                    "author_name": self.name,
                                    "color": "danger",
                                    "pretext": "[SCRAPER] New Alert for failing scrapers",
                                    "fields": [
                                        {
                                            "title": error_name,
                                            "value": message,
                                            "short": False
                                            },
                                            {
                                            "title": "Failing Domains",
                                            "value": self.domains(),
                                            "short": False
                                            },
                                            {
                                            "title": "Machine Location",
                                            "value": "{}".format(getpass.getuser()),
                                            "short": True
                                            },
                                            {
                                            "title": "Time",
                                            "value": str(time.ctime()),
                                            "short": True
                                            },
                                        ],
                                    }
                                ]
                        }
        response = requests.post(
            webhook_url, data=json.dumps(slack_data),
            headers={'Content-Type': 'application/json'}
        )



    def errback(self, failure):
        self.logger.error(repr(failure))
        if failure.check(HttpError):
            # these exceptions come from HttpError spider middleware
            error_name = 'HttpError'
            message = "Spider failure caused by exceptions from HttpError spider middleware due to non-200 response " \
                    + "on the request url %s"  % failure.request.url
            print ("SCRAPPER ERROR MESSAGE",failure.__dict__)

            self.notification(error_name, message)

            response = failure.value.response
            self.logger.error('HttpError on %s', response.url)

        elif failure.check(DNSLookupError):
            # these exceptions come from DNSLookupError spider middleware
            error_name = 'DNSLookupError'
            message = 'Spider failure caused by exceptions from DNSLookupError spider middleware '\
                    + "on the request url %s"  % failure.request.url
            print ("SCRAPPER ERROR MESSAGE",failure.__dict__)
            
            self.notification(error_name, message)
            
            response = failure.value.response
            self.logger.error('DNSLookUpError on %s', response.url)

            
        elif failure.check(TimeoutError, TCPTimedOutError):
            # these exceptions come from TCPTimeOutError spider middleware
            error_name = 'TCPTimedOutError'
            message = "Spider failure caused by exceptions from TCPTimedOutError spider middleware %s" \
                    + "on the request url %s"  % failure.request.url

            self.notification(error_name, message)
            
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
    