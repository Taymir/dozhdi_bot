import json
import pymongo
import settings
from progress.bar import IncrementalBar
import time

client = pymongo.MongoClient(host=settings.mongodb['host'], port=settings.mongodb['port'],
                             username=settings.mongodb['username'], password=settings.mongodb['password'],
                             tls=settings.mongodb['tls'])
db = client.dozhdi_bot

f = open("cities.json", 'r')
cities_arr = json.load(f)

bar = IncrementalBar("Importing cities", max = len(cities_arr))
docs = []
for city in cities_arr:
    name = city['Город']
    region = city['Регион']
    if name == "":
        name = region

    lat = city['Широта']
    lon = city['Долгота']

    docs.append({
        'city': name,
        'location': [lon, lat]
    })
    bar.next()

db.cities.insert_many(docs)
