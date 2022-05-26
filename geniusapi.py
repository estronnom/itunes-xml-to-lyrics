import xml
import aiohttp
import asyncio
import logging
from xml.etree import ElementTree
from bs4 import BeautifulSoup as bs
import json

task_list = []
logging.basicConfig(filename='lyricsapp.log', encoding='utf-8', level=logging.INFO,
                    format='%(levelname)s:%(asctime)s:%(message)s')


async def check_token_validity(api_key, session):
    url = f'https://api.genius.com/search?access_token={api_key}'
    async with session.get(url) as response:
        return response.status == 200


def write_lyrics(lyrics, title, artist, token, r, url):
    if not lyrics:
        r.rpush(f'{token}-output', f'{artist} - {title}\nNot found!')
    else:
        song_lyrics = [f'{artist} - {title}', url]
        for lyric in lyrics:
            for tag in lyric:
                if not tag.name or tag.name == 'a':
                    if len(tag.text) > 1000:
                        return
                    song_lyrics.append(tag.text)
        if len(song_lyrics) > 150:
            return
        r.rpush(f'{token}-output', '\n'.join(song_lyrics))
        logging.info(f'{token}:{artist}:{title}:lyrics retrieved')


async def parse_lyrics(path, title, artist, session, token, r):
    url = f'https://genius.com{path}'
    async with session.get(url) as response:
        data = await response.read()
    soup = bs(data, 'lxml')
    lyrics = soup.find_all('div', {'data-lyrics-container': 'true'})
    if lyrics:
        write_lyrics(lyrics, title, artist, token, r, url)
    else:
        logging.info(f'{token}:{artist}:{title}:lyrics not found')
        write_lyrics(None, title, artist, token, r, None)


async def parse_artist(title, artist, api_key, session, token, r):
    url = f'https://api.genius.com/search?access_token={api_key}&q={artist.replace(" ", "+")}+{title.replace(" ", "+")}'
    async with session.get(url) as response:
        data = await response.read()
    try:
        json_got = json.loads(data)
        path = json_got['response']['hits'][0]['result']['path']
        path_words = [i.lower() for i in path.split('-')]
        if title.lower() not in path_words and artist.lower() not in path_words:
            raise IndexError
        logging.info(f'{token}:{artist}:{title}:id retrieved')
        task = asyncio.create_task(parse_lyrics(path, title, artist, session, token, r))
        task_list.append(task)
    except Exception as exc:
        logging.info(f'{token}:{artist}:{title}:lyrics not found')
        write_lyrics(None, title, artist, token, r, None)


async def dispatcher(api_key, file, token, r):
    try:
        root = ElementTree.fromstring(file)
    except xml.etree.ElementTree.ParseError:
        r.set(f'{token}-status', 'Unable to parse file')
        r.expire(f'{token}-status', 60 * 30)
        return
    async with aiohttp.ClientSession(trust_env=True) as session:
        valid = await check_token_validity(api_key, session)
        if not valid:
            r.set(f'{token}-status', 'Invalid Genius API Token')
            r.expire(f'{token}-status', 60 * 30)
            return
        parse_result = root.findall('./dict/dict/dict')
        if not parse_result:
            r.set(f'{token}-status', 'Unable to parse file')
            r.expire(f'{token}-status', 60 * 30)
            return
        for index, item in enumerate(parse_result):
            if (index + 1) % 15 == 0:
                await asyncio.sleep(2)
                r.set(f'{token}-status', f'{index + 1} songs retrieved')
            try:
                title = item[3].text
                artist = item[5].text
            except IndexError:
                continue
            task = asyncio.create_task(parse_artist(title, artist, api_key, session, token, r))
            task_list.append(task)
        try:
            await asyncio.gather(*task_list)
            await asyncio.sleep(5)
        finally:
            r.set(f'{token}-status', 'Done')
            r.expire(f'{token}-status', 60 * 30)
            r.expire(f'{token}-output', 60 * 30)
