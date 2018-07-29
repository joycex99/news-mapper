# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class NewsCrawlerItem(scrapy.Item):
    url = scrapy.Field()
    title = scrapy.Field()
    description = scrapy.Field()
    keywords = scrapy.Field()
    date = scrapy.Field()
    content = scrapy.Field()
    locations = scrapy.Field()
    
    def __repr__(self):
        """only print out attr1 after exiting the Pipeline"""
        return repr({"title": self["title"], "date": self["date"]})
