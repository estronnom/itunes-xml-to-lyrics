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


async def get_status(token):
    status = r.get(f'{token}-status')
    if not status:
        raise web.HTTPNotFound()
    else:
        return status.decode()


@routes.get('/', name='index')
@aiohttp_jinja2.template('index.html')
async def index(request):
    return


@routes.post('/', name='index_post')
async def index_post(request):
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
@aiohttp_jinja2.template('result.html')
async def result_page(request):
    token = request.match_info['token']
    status = await get_status(token)
    return {"token": token, "status": status}


@routes.post('/{token}/status', name='status_update')
async def status_update(request):
    token = request.match_info['token']
    status = await get_status(token)
    data = {'status': status}
    return web.json_response(data)


@routes.post('/{token}', name='lyrics_download')
async def lyrics_download(request):
    token = request.match_info['token']
    headers = {
        "Content-disposition": f"attachment; filename={token}-lyrics.txt"
    }
    output_list = r.lrange(f'{token}-output', 0, -1)
    if not output_list:
        raise web.HTTPNotFound()
    body = '\n\n'.join([i.decode() for i in output_list])
    return web.Response(headers=headers, body=body)


app = web.Application()
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))
routes.static('/templates', 'templates/')
app.add_routes(routes)

if __name__ == '__main__':
    web.run_app(app, port=8080)
