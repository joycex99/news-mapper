import spacy
from newspaper import Article
from collections import defaultdict

nlp = spacy.load('en')

def find_ents(url, body=False):
    article = Article(url)
    article.download()
    article.parse()
    if body:
        doc = nlp(article.title + article.text)
    else:
        doc = nlp(article.title)

    ent_dict = defaultdict(int)
    for ent in doc.ents:
        print(ent.text, ent.label_)
        if ent.label_ == "GPE" or ent.label_ == "LOC":
            ent_dict[ent.text] += 1
    print("____________")
    return ent_dict