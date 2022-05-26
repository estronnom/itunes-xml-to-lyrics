# ITunes XML Lyrics Parser

This web app allows you to simply parse lyrics for your whole Itunes library from genius.com.
App is running flawless using docker-compose. App is based on aiohttp library, which guarantees high performance.

# Running web app
Clone repository

`git clone https://github.com/estronnom/itunes-xml-to-lyrics.git`

Proceed to new directory

`cd itunes-xml-to-lyrics`

Run docker-compose

`docker-compose up -d`

Visit [localhost:8080](localhost:8080) and follow further page instructions

Sometimes docker run web app on docker-machine ip, so it may be useful to evaluate
`docker-machine ip`
