import pkg_resources
import aiohttp_jinja2

from aiocache import cached, SimpleMemoryCache
from aiohttp import web
from nulsexplorer.web import app
from nulsexplorer.model.consensus import Consensus
from nulsexplorer.model.transactions import Transaction
from nulsexplorer.model.blocks import (Block, find_blocks, find_block,
                                       get_last_block_height)
from .utils import Pagination, PER_PAGE

app.router.add_static('/static/',
                      path=pkg_resources.resource_filename('nulsexplorer.web', 'static/'),
                      name='static')

@aiohttp_jinja2.template('index.html')
async def index(request):
    """Index of the block explorer.
    """
    last_blocks = [block async for block
                   in Block.find({}, limit=10, sort=[('height', -1)])]

    return {'last_blocks': last_blocks,
            'last_height': await get_last_block_height()}
app.router.add_get('/', index)

async def broadcast(request):
    """ Forward the broadcast to the API Server for now.
    """

    data = await request.json()

    async with ClientSession() as session:
        output = await api_post(session,
                                'accountledger/transaction/broadcast',
                                data)

    return web.json_response(output)

app.router.add_post('/broadcast', broadcast)
