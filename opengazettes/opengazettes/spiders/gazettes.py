# -*- coding: utf-8 -*-
import scrapy
from datetime import datetime
from ..items import OpengazettesItem
import romanify


class GazettesSpider(scrapy.Spider):
    name = "gazettes"
    allowed_domains = ["kenyalaw.org"]
    start_urls = ['http://kenyalaw.org/kenya_gazette/gazette/year/2006']

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
        # Set PDF filename and download to S3
        # Set file URLs to be downloaded by the files pipeline
        item['file_urls'] = [item['download_link']]
        yield item
