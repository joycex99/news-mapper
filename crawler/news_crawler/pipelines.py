from scrapy.exceptions import DropItem

from newspaper.configuration import Configuration
from newspaper.extractors import ContentExtractor 
from newspaper.cleaners import DocumentCleaner
from newspaper.outputformatters import OutputFormatter 


# import pycountry
# import geocoder
import spacy
from collections import Counter
import datetime
import dateutil.parser as date_parser
import csv
import json

import pymongo

import logging

# !! explore newspaper.nlp to get keywords

class ArticleExtractionPipeline(object):
    def __init__(self):
        self.config = Configuration()                    # sets meta config for article and parser
        self.parser = self.config.get_parser()           # parser
        self.extractor = ContentExtractor(self.config)   # extracts info (author, tags, text, etc.) from parsed article
        self.doc_cleaner = DocumentCleaner(self.config)  # cleans unwanted tags and nodes from DOM 
        self.formatter = OutputFormatter(self.config)    # outputs formatted text from parsed xpath nodes

    
    # right now basically only works for RT
    # params: doc is parsed html from self.parser
    def find_date_from_html(self, doc): 
        # https://github.com/Webhose/article-date-extractor/blob/master/articleDateExtractor/__init__.py
        candidates = self.parser.getElementsByTag(doc, tag="time") # add more
        times = []
        for candidate in candidates:
            time_string = candidate.text
            for indicator in ["Edited", "Updated", "Published"]:  
                if indicator in time_string:
                    # indicator probably followed by "at" or ":", actual time is after that
                    if "at" in time_string:
                        time_string = time_string.split("at", 1)[1]
                    elif ":" in time_string:
                        time_string = time_string.split(":", 1)[1]
                    break
            time = self.datetime_from_str(time_string)
            if time:
                times.append(time)
        if times:
            return min(times)
        else:
            return None

    def datetime_from_str(self, datetime_string):
        try: 
            return date_parser.parse(datetime_string).replace(tzinfo=None) # otherwise can't compare naive and (timezone) offset-aware times
        except (ValueError, OverflowError, AttributeError, TypeError):
            return None


    # params: doc is parsed html from self.parser
    # TODO: generalize
    def get_date(self, url, doc):
        raw_date = (self.extractor.get_publishing_date(url, doc) or # telesur, africanews
                    self.extractor.get_meta_content(doc, "meta[name='LastModifiedDate']") or # aljazeera, Sun, 07 January 2018 18:36:49 GMT
                    self.extractor.get_meta_content(doc, "meta[name='Last-Modified']") or # times of india, Jan 9, 2018, 05:18 IST
                    self.extractor.get_meta_content(doc, "meta[property='og:updated_time']"))  # diplomat, "2018-01-05 23:22:46"
        if raw_date:
            return self.datetime_from_str(raw_date)
        else:
            return self.find_date_from_html(doc)

    # params: date is datetime object
    def recent_article(self, date, max_days_elapsed=3):
        return datetime.datetime.now() - date < datetime.timedelta(days=max_days_elapsed)


    def process_item(self, item, spider):
        doc = self.parser.fromstring(item["content"])

        item["title"] = self.extractor.get_title(doc)
        item["description"] = self.extractor.get_meta_description(doc)
        item["keywords"] = (self.extractor.get_meta_content(doc, "meta[name='news_keywords']") or
                            self.extractor.get_meta_keywords(doc))
        item["date"] = self.get_date(item["url"], doc)

        # drop item if no date
        if not item["date"] or not self.recent_article(item["date"], max_days_elapsed=7): # or not self.recent_article(item["date"])
            raise DropItem("Missing or invalid date for: {}".format(item["title"]))
        
        # clean:
        clean_doc = self.doc_cleaner.clean(doc)
        top_node = self.extractor.post_cleanup(
                     self.extractor.calculate_best_node(clean_doc)
                   )
        item["content"] = self.formatter.get_formatted(top_node)[0] # [1] returns html of article

        # drop item if article too short
        if len(item["content"]) < 600:
            raise DropItem("Not enough text: {}".format(item["title"]))


        logging.info("ARTICLE TITLE: {}".format(item["title"]))
        logging.info("\t time: {}".format(item["date"]))
        return item



class LocationTaggerPipeline(object):
    def __init__(self):
        self.nlp = spacy.load('en')
        self.city_file = "./news_crawler/cities_basic.csv"
        self.countries_file = "./news_crawler/countries.json"
        self.countries = self.countries_from_file()
        self.cities = self.cities_from_file() # TODO: enter into DB
        # ?? self.coordinates = {}
        

    ''' Returns map of {country: [alpha-2 code, latlng]} '''
    def countries_from_file(self):
        countries = {}
        with open(self.countries_file, "r") as f:
            country_data = json.load(f)
            for country in country_data:
                name = country["name"]["common"]
                alpha_2 = country["cca3"]
                latlng = country["latlng"]
                countries[name] = [alpha_2, latlng]
        return countries 


    ''' Returns map of {city: [country, population]} '''
    def cities_from_file(self):
        cities = {}     
        with open(self.city_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                city = row["city_ascii"]
                country = self.preprocess_location(row["country"])
                if city not in cities:
                    cities[city] = [country, row["pop"]]
                else:
                    # if same city name already in db, keep the one with the bigger population
                    if row["pop"] > cities[city][1]:
                        cities[city] = [country, row["pop"]]
        return cities


    ''' params: location is string ''' 
    def preprocess_location(self, location):
        if location[-2:] == "'s": 
            location = location[:-2] # Russia's => Russia
        # TODO: find alternate names list
        if location in ["US", "U.S.", "USA", "U.S.A", "America", "the United States", "United States of America"]:
            location = "United States"

        if location in ["UK", "U.K."]:
            location = "United Kingdom"

        if location in ["Gaza", "the Gaza Strip", "West Bank", "the West Bank"]:
            location = "Palestine"

        # TODO: redirect jeruselum to both
                    
        return location 


    ''' deprecated (?) '''
    def is_country(self, loc_name):
        # TODO: use this: https://github.com/ushahidi/geograpy/blob/master/geograpy/places.py#L50
        try: 
            pycountry.countries.get(name=loc_name)
            return True
        except KeyError:
            return False


    ''' params
            locations: array of up to 3 locations '''
    def tag_item(self, locations):
        tags = set()
        for location in locations:
            location = self.preprocess_location(location)
            if location in self.countries and len(tags) < 2:
                tags.add(location)
                
            # TODO: add subregions?

            else: # assume city
                if location in self.cities and len(tags) < 2:
                    tags.add(self.cities[location][0])

        return list(tags)

    # params: spacy nlp docs of the title, description, and body of article
    # returns: Counter() objection with location entities and counts 
    def extract_locations(self, title, description, body):
        ent_cnt = Counter()

        for ent in (title.ents + description.ents + body.ents):
            if ent.label_ == "GPE" or ent.label_ == "LOC":
                ent_cnt[ent.text] += 1

        for ent in ent_cnt: 
            if ent in [e.text for e in description.ents]:
                ent_cnt[ent] *= 1.25
            if ent in [e.text for e in title.ents]:
                ent_cnt[ent] *= 1.5
        # for category, booster in CATEGORY_VALS.items():
        #     for ent in category.ents:
        #         if ent.label_ == "GPE" or ent.label_ == "LOC":
        #             ent_cnt[ent.text] += 1

        return ent_cnt


    def process_item(self, item, spider):

        # use spaCy to parse article's title, descrip, and text
        title = self.nlp(item["title"])
        description = self.nlp(item["description"])
        body = self.nlp(item["content"])

        # TODO: make relative to total occurences, e.g. 1.5x instead of +3 
        CATEGORY_VALS = {title: 3, description: 2, body: 1}

        # build counter of each location's number of mentions, boosted by appearences in title and descrip. 
        ent_cnt = self.extract_locations(title, description, body)
                
        # remove all locations that are mentioned fewer than 2 times
        for loc, v in list(ent_cnt.items()):
            if v < 2:
                ent_cnt.pop(loc)

        logging.info("\t LOCACTIONS: {}".format(ent_cnt.most_common(3)))

        if ent_cnt:
            # remove all locations that are mentioned fewer than half as many times as the most common location
            max_count = ent_cnt.most_common(1)[0][1]
            locs = [tup[0] for tup in ent_cnt.most_common(3) if tup[1]/max_count >= 0.5]
            
            # tag item w/ locations
            tags = self.tag_item(locs)
            if tags:
                if len(tags) == 2:
                    logging.info("\t -----------------")
                logging.info("\t COUNTRIES TO TAG: {}".format(list(tags)))

                item["locations"] = tags
                return item 

        raise DropItem("No locations tagged: {}".format(item["title"]))

        


class DatabasePipeline(object):

    def __init__(self, mongo_host, mongo_port, mongo_name, mongo_user, mongo_pass):
        self.db_host = mongo_host
        self.db_port = mongo_port
        self.db_name = mongo_name 
        self.db_user = mongo_user 
        self.db_pass = mongo_pass 
        self.collection_name = 'articles'

    # https://julien.danjou.info/blog/2013/guide-python-static-class-abstract-methods
    # http://python-3-patterns-idioms-test.readthedocs.io/en/latest/Factory.html
    @classmethod 
    def from_crawler(cls, crawler):
        return cls(
            mongo_host = crawler.settings.get("DB_HOST"),
            mongo_port = crawler.settings.get("DB_PORT"),
            mongo_name = crawler.settings.get("DB_NAME"),
            mongo_user = crawler.settings.get("DB_USER"),
            mongo_pass = crawler.settings.get("DB_PASS")
        )

    def open_spider(self, spider):
        self.connection = pymongo.MongoClient(self.db_host, self.db_port)
        self.db = self.connection[self.db_name]
        self.db.authenticate(self.db_user, self.db_pass)
        logging.info("----- Successfully connected to mongo ----- ")

    def close_spider(self, spider):
        self.connection.close()
        logging.info("----- Successfully closed mongo connection ----- ")

    def process_item(self, item, spider):
        # save everything but the actual html and text of article
        news_item = {k: v for k, v in dict(item).items() if k != "content"}
        logging.info("\t {}".format(news_item.values()))

        self.db[self.collection_name].insert_one(news_item)

        return item 


# https://realpython.com/blog/python/primer-on-python-decorators/
# decorators: "wraps" the following function in the function mentioned in the @ symbol, 
#             i.e. passes the following function as an argument into the @ function
    


# DB_NAME = world-news         # database_name  
# DB_HOST = ds143907.mlab.com  # dsxxxxxx.mlab.com
# DB_PORT = 43907              # 12345
# DB_USER = joycexu            # user 
# DB_PASS = news               # pass

# connection = MongoClient(DB_HOST, DB_PORT)
# db = connection[DB_NAME]
# db.authenticate(DB_USER, DB_PASS)










