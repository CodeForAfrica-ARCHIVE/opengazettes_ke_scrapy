# -*- coding: utf-8 -*-
import scrapy


class GazettesSpider(scrapy.Spider):
    name = "gazettes"
    allowed_domains = ["kenyalaw.org"]
    start_urls = ['http://kenyalaw.org/']

    def parse(self, response):
        pass
