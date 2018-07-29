import scrapy
from scrapy.spiders import CrawlSpider, Rule 
from scrapy.linkextractors import LinkExtractor
from news_crawler.items import NewsCrawlerItem
import newspaper.urls as news_urls 

# start urls = top level domains for news sites
    # worldcrunch, al-monitor, spiegel.de
    # https://www.quora.com/What-is-the-best-source-of-world-news

    # http://watchingamerica.com/WA/foreign-news-sources/
    # https://en.wikipedia.org/wiki/International_news_channels

    # Africanews, Telesur, Times of India, South China Morning Post (HK), Dawn (Pakistan)
    # http://foreignpolicy.com/2015/04/15/why-we-cant-just-read-english-newspapers-to-understand-terrorism-big-data/


class ProcessedLinkExtractor(LinkExtractor):
    ''' caller should be class that implements process_links
        process_links should be the name of a function in the caller that takes a list 
                      of links and returns a processed one'''
    def __init__(self, caller=None, process_links='', **kwargs):
        self.caller = caller
        self.process_links = process_links
        super().__init__(**kwargs)

    def extract_links(self, response):
        orig_links = super().extract_links(response)
        link_processor = (getattr(self.caller, self.process_links) 
                            if hasattr(self.caller, self.process_links) else None)
        if link_processor:
            return link_processor(orig_links)
        else:
            return orig_links 



''' 

^.*video.*$

safe_urls = ['/video', '/slide', '/gallery', '/powerpoint',
                     '/fashion', '/glamour', '/cloth']   


aljazeera: /inpictures, http://www.aljazeera.com/indepth/inpictures/week-pictures-kabul-blast-egypt-attack-171229215445312.html
telesur: /multimedia, https://www.telesurtv.net/english/multimedia/Palestinians-Resist-Occupation-20171230-0017.html


^.*DEF.*$

^((?!video).)*$''' 




class NewsSpider(CrawlSpider):
    name = "news"
    allowed_domains = ["www.aljazeera.com"]
    start_urls = ["http://www.aljazeera.com/"]

    # allowed_domains = ["africanews.com"]
    # start_urls = ["http://www.africanews.com/"]  

    # allowed_domains = ["telesurtv.net"] 
    # start_urls = ["https://www.telesurtv.net/english/"] 

    # allowed_domains = ["thediplomat.com"] # or asia times????
    # start_urls = ["https://thediplomat.com/"]

    # allowed_domains = ["rt.com"]
    # start_urls = ["https://www.rt.com/"]


    rules = (
        Rule(LinkExtractor(deny=('^.*\/video.*$', '^.*\/slide.*$', '^.*\/gallery.*$', 
                                 '^.*\/inpictures.*$', '^.*\/multimedia.*$')), 
             process_links='process_links', follow=True, callback='parse_item'),
    )

    # takes in list of scrapy.link.Link objs
    def process_links(self, links):
        return [link for link in links if news_urls.valid_url(link.url)]


    def parse_item(self, response):
        # item pipeline: add another to filter out one with too short of a body, or a media source (vid)

        item = NewsCrawlerItem()
        item["url"] = response.url 
        item["content"] = response.body

        yield item