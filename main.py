import asyncio

import aiohttp_jinja2
import jinja2
import redis
from aiohttp import web
from geniusapi import dispatcher
import secrets
import io

routes = web.RouteTableDef()
r = redis.Redis()


@routes.get('/', name='index')
@aiohttp_jinja2.template('index.html')
async def index(request):
    return


@routes.post('/', name='index_post')
async def post_handler(request):
    reader = await request.multipart()
    field = await reader.next()
    assert field.name == 'key'
    api_key = await field.read()
    api_key = api_key.decode()
    field = await reader.next()
    assert field.name == 'xml'
    token = secrets.token_urlsafe(8)
    with io.BytesIO() as f:
        while True:
            chunk = await field.read_chunk()
            if not chunk:
                break
            f.write(chunk)
        xml_string = f.getvalue().decode()
        r.set(f'{token}-status', 'Reading XML file...')
        asyncio.create_task(dispatcher(api_key, xml_string, token, r))
    raise web.HTTPFound(location=request.app.router['result_page'].url_for(token=token))


@routes.get('/{token}', name='result_page')
async def key_handler(request):
    token = request.match_info['token']
    status = r.get(f'{token}-status')
    if not status:
        raise web.HTTPNotFound()
    if status.decode() == 'Done':
        output_list = r.lrange(f'{token}-output', 0, -1)
        content = '\n\n'.join([i.decode() for i in output_list])
        return web.Response(body=content, content_type='text/plain')
    else:
        return web.Response(
            text=f"Your query is being processed...\n{r.get(f'{token}-status')}")


app = web.Application()
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))
app.add_routes(routes)
web.run_app(app)
