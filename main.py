import asyncio

import aiohttp_jinja2
import jinja2
from aiohttp import web
from geniusapi import dispatcher
import io

routes = web.RouteTableDef()


@routes.get('/', name='index')
@aiohttp_jinja2.template('index.html')
async def index(request):
    return


@routes.post('/', name='index_post')
async def post_handler(request):
    reader = await request.multipart()
    field = await reader.next()
    assert field.name == 'key'
    key = await field.read()
    field = await reader.next()
    assert field.name == 'xml'
    filename = field.filename
    with io.BytesIO() as f:
        while True:
            chunk = await field.read_chunk()
            if not chunk:
                break
            f.write(chunk)
        xml_string = f.getvalue().decode()
        asyncio.create_task(dispatcher(key, xml_string))
    raise web.HTTPFound(location=request.app.router['result_page'].url_for(key='biba'))


@routes.get('/{key}', name='result_page')
async def key_handler(request):
    return web.Response(text=f"You got to a results page. Request match info is {request.match_info['key']}")


app = web.Application()
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))
app.add_routes(routes)
web.run_app(app)
