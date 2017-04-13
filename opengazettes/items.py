# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class OpengazettesItem(scrapy.Item):
    # define the fields for your item here like:
    gazette_link = scrapy.Field()
    publication_date = scrapy.Field()
    gazette_volume = scrapy.Field()
    gazette_number = scrapy.Field()
    download_link = scrapy.Field()
    file_urls = scrapy.Field()
    files = scrapy.Field()
    filename = scrapy.Field()
    special_issue = scrapy.Field()
