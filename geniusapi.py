import xml.etree.ElementTree

import aiohttp
import asyncio
from xml.etree import ElementTree
from bs4 import BeautifulSoup as bs
import json

task_list = []


def write_lyrics(lyrics, title, artist, token, r, url):
    if not lyrics:
        r.rpush(f'{token}-output', f'{artist} - {title}\nNot found!')
    else:
        song_lyrics = [f'{artist} - {title}', url]
        for lyric in lyrics:
            for tag in lyric:
                if not tag.name or tag.name == 'a':
                    if len(tag.text) > 500:
                        return
                    song_lyrics.append(tag.text)
        if len(song_lyrics) > 150:
            return
        r.rpush(f'{token}-output', '\n'.join(song_lyrics))


async def parse_lyrics(path, title, artist, session, token, r):
    url = f'https://genius.com{path}'
    async with session.get(url) as response:
        data = await response.read()
    soup = bs(data, 'lxml')
    lyrics = soup.find_all('div', {'data-lyrics-container': 'true'})
    if lyrics:
        write_lyrics(lyrics, title, artist, token, r, url)
        print(f'retrieved lyrics of {path}')


async def parse_artist(title, artist, api_key, session, token, r):
    url = f'https://api.genius.com/search?access_token={api_key}&q={artist.replace(" ", "+")}+{title.replace(" ", "+")}'
    async with session.get(url) as response:
        data = await response.read()
    try:
        json_got = json.loads(data)
        path = json_got['response']['hits'][0]['result']['path']
        print(f'retrieved id of {artist}-{title}')
        task = asyncio.create_task(parse_lyrics(path, title, artist, session, token, r))
        task_list.append(task)
    except Exception as exc:
        print(f'EXCEPTION {artist}-{title} {exc}')
        write_lyrics(None, title, artist, token, r, None)


async def dispatcher(api_key, file, token, r):
    try:
        root = ElementTree.fromstring(file)
    except xml.etree.ElementTree.ParseError as exc:
        print(exc)
        return
    async with aiohttp.ClientSession() as session:
        parse_result = root.findall('./dict/dict/dict')
        if not parse_result:
            r.set(f'{token}-status', 'Unable to parse file...')
            r.expire(f'{token}-status', 60 * 30)
            return
        for index, item in enumerate(parse_result):
            if (index + 1) % 15 == 0:
                await asyncio.sleep(5)
                r.set(f'{token}-status', f'{index + 1} songs retrieved')
            title = item[3].text
            artist = item[5].text
            task = asyncio.create_task(parse_artist(title, artist, api_key, session, token, r))
            task_list.append(task)
        await asyncio.sleep(10)
        await asyncio.gather(*task_list)
    r.set(f'{token}-status', 'Done')
    r.expire(f'{token}-status', 60 * 30)
    r.expire(f'{token}-output', 60 * 30)
