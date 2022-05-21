import xml.etree.ElementTree

import aiohttp
import asyncio
from xml.etree import ElementTree
from bs4 import BeautifulSoup as bs
import json

task_list = []


def write_lyrics(lyrics, title, artist, token, r):
    song_lyrics = [f'{title} - {artist}']
    for lyric in lyrics:
        for tag in lyric:
            if not tag.name or tag.name == 'a':
                song_lyrics.append(tag.text)
    r.rpush(f'{token}-output', '\n'.join(song_lyrics))


async def parse_lyrics(path, title, artist, session, token, r):
    url = f'https://genius.com{path}'
    async with session.get(url, allow_redirects=True) as response:
        data = await response.read()
    soup = bs(data, 'lxml')
    lyrics = soup.find_all('div', {'data-lyrics-container': 'true'})
    if lyrics:
        write_lyrics(lyrics, title, artist, token, r)
        print(f'retrieved lyrics of {path}')


async def parse_artist(title, artist, api_key, session, token, r):
    url = f'https://api.genius.com/search?access_token={api_key}&q={artist.replace(" ", "+")}+{title.replace(" ", "+")}'
    async with session.get(url, allow_redirects=True) as response:
        data = await response.read()
    try:
        json_got = json.loads(data)
        path = json_got['response']['hits'][0]['result']['path']
        print(f'retrieved id of {artist}-{title}')
        task = asyncio.create_task(parse_lyrics(path, title, artist, session, token, r))
        task_list.append(task)
    except Exception as exc:
        print(f'EXCEPTION {artist}-{title} {exc}')


async def dispatcher(api_key, file, token, r):
    try:
        root = ElementTree.fromstring(file)
    except xml.etree.ElementTree.ParseError as exc:
        print(exc)
        return
    async with aiohttp.ClientSession() as session:
        for index, item in enumerate(root.findall('./dict/dict/dict')):
            if (index + 1) % 15 == 0:
                await asyncio.sleep(5)
                r.set(f'{token}-status', f'{index + 1} songs retrieved')
            title = item[3].text
            artist = item[5].text
            task = asyncio.create_task(parse_artist(title, artist, api_key, session, token, r))
            task_list.append(task)
            # if index > 30:
            #     break
        await asyncio.gather(*task_list)
    r.set(f'{token}-status', 'Done')
    r.expire(f'{token}-status', 60 * 5)
    r.expire(f'{token}-output', 60 * 5)
