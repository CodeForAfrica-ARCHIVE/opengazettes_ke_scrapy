# -*- coding: utf-8 -*-
import scrapy
from datetime import datetime
from ..items import OpengazettesItem
import romanify


class GazettesSpider(scrapy.Spider):
    name = "gazettes"
    allowed_domains = ["kenyalaw.org"]

    def start_requests(self):
        # Get the year to be crawled from the arguments
        # The year is passed like this: scrapy crawl gazettes -a year=2017
        year = self.year
        url = 'http://kenyalaw.org/kenya_gazette/gazette/year/%s' % \
            (year)
        yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        # Extract all gazette links
        # Add publication date to metadata from table data
        rows = response.css('#content tr')
        for row in rows:
            gazette_meta = OpengazettesItem()
            gazette_meta['gazette_link'] = row.xpath(
                'td/a/@href').extract_first()
            if gazette_meta['gazette_link']:
                # Add volume and issue number to metadata from URL
                gazette_meta['gazette_volume'] = romanify.roman2arabic(
                    row.xpath('td/a/@href').re(r'Vol.*.*[""|-]')[0]
                    .replace('Vol.', '').replace('-', '').replace(' ', ''))
                gazette_meta['gazette_number'] = row.xpath('td/a/@href').re(
                    r'No.*.*')[0].replace('No.', '').replace(' ', '')
                # Add publication date to metadata from table data
                gazette_meta['publication_date'] = datetime.strptime(
                    row.xpath('td/text()')[1].extract(), '%d %B,%Y')
                request = scrapy.Request(gazette_meta['gazette_link'],
                                         callback=self.open_single_gazette)
                request.meta['gazette_meta'] = gazette_meta
                yield request

    # Visit individual gazettes links
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
        # Set PDF filename
        item['filename'] = 'opengazettes-ke-vol-%s-no-%s-dated-%s-%s-%s' % \
            (item['gazette_volume'], item['gazette_number'],
                item['publication_date'].strftime("%d"),
                item['publication_date'].strftime("%B"),
                item['publication_date'].strftime("%Y"))
        # Set file URLs to be downloaded by the files pipeline
        item['file_urls'] = [item['download_link']]
        yield item
