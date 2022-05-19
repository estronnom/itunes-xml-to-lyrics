import xml.etree.ElementTree

import aiohttp
import asyncio
from xml.etree import ElementTree
from bs4 import BeautifulSoup as bs
import json


async def parse_lyrics(path, title, artist, session):
    print(f'retrieving lyrics of {path}')
    url = f'https://genius.com{path}'
    async with session.get(url, allow_redirects=True) as response:
        data = await response.read()
    soup = bs(data, 'lxml')
    lyrics = soup.find_all('div', {'data-lyrics-container': 'true'})
    if lyrics:
        print(f'Writing lyrics for {path}')


async def parse_artist(title, artist, key, session):
    print(f'retrieving id of {artist}-{title}')
    url = f'https://api.genius.com/search?access_token={key}&q={artist}+{title}'
    async with session.get(url, allow_redirects=True) as response:
        data = await response.read()
    try:
        json_got = json.loads(data)
        path = json_got['response']['hits'][0]['result']['path']
        asyncio.create_task(parse_lyrics(path, title, artist, session))
    except Exception as exc:
        print(f'{artist}-{title} {exc}')


async def dispatcher(key, file):
    # try:
    #     root = ElementTree.fromstring(file.getvalue()).getroot()
    # except xml.etree.ElementTree.ParseError as exc:
    #     print(exc)
    root = ElementTree.fromstring(file)
    task_list = list()
    async with aiohttp.ClientSession() as session:
        for index, item in enumerate(root.findall('./dict/dict/dict')):
            print('found', index, item)
            if index % 20 == 0:
                await asyncio.sleep(10)
            title = item[3].text
            artist = item[5].text
            task = asyncio.create_task(parse_artist(title, artist, key, session))
            task_list.append(task)
        await asyncio.gather(*task_list)
