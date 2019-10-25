import asyncio
import aiohttp
import logging
import base64
import operator

from aiohttp import web, ClientSession
import functools
import jsonrpc_base
from jsonrpc_base import JSONRPCError, TransportError, ProtocolError

from nulsexplorer.web import app
from nulsexplorer import model
from nulsexplorer.model.blocks import get_last_block_height, store_block
from nulsexplorer.model.transactions import Transaction
from nulsexplorer.model.consensus import Consensus
from nulsexplorer.modules.register import do_batch_postprocess, do_block_postprocess

LOGGER = logging.getLogger('connector')


class Server(jsonrpc_base.Server):
    """A connection to a HTTP JSON-RPC server, backed by aiohttp"""

    def __init__(self, url, session=None, *, loads=None, content_type=-1, **post_kwargs):
        super().__init__()
        if session is None:
            conn = aiohttp.TCPConnector(limit=200)
            session = aiohttp.ClientSession(connector=conn)
        object.__setattr__(self, 'session', session)
        post_kwargs['headers'] = post_kwargs.get('headers', {})
        post_kwargs['headers']['Content-Type'] = post_kwargs['headers'].get(
            'Content-Type', 'application/json')
        post_kwargs['headers']['Accept'] = post_kwargs['headers'].get(
            'Accept', 'application/json-rpc')
        self._request = functools.partial(self.session.post, url, **post_kwargs)

        self._json_args = {}
        if loads is not None:
            self._json_args['loads'] = loads
        if content_type != -1:
            self._json_args['content_type'] = content_type

    @asyncio.coroutine
    def send_message(self, message):
        """Send the HTTP message to the server and return the message response.
        No result is returned if message is a notification.
        """
        try:
            response = yield from self._request(data=message.serialize())
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            raise TransportError('Transport Error', message, exc)

        if response.status != 200:
            raise TransportError('HTTP %d %s' % (response.status, response.reason), message)

        if message.response_id is None:
            # Message is notification, so no response is expcted.
            return None

        try:
            response_data = yield from response.json(**self._json_args)
        except ValueError as value_error:
            raise TransportError('Cannot deserialize response body', message, value_error)

        return message.parse_response(response_data)

async def get_server():
    base_uri = app['config'].nuls.base_uri.value
    return Server(base_uri, content_type=None)

async def request_last_height(server, chain_id):
    last_height = -1
    try:
        resp = await server.getBestBlockHeader(chain_id)
        if resp is not None:
            last_height = resp.get('height', -1)
    except Exception:
        LOGGER.exception("Can't get last block height for chain_id %d" % chain_id)
    return last_height

async def request_block(server, chain_id, height=None, hash=None):
    block = {}
    if height is not None:
        block = await server.getBlockByHeight(chain_id, height)
    elif hash is not None:
        block = await server.getBlockByHash(chain_id, hash)
    else:
        raise ValueError("Neither height nor hash set for block request")
    
    block['header']['chainId'] = chain_id

    return block


async def request_consensus(server, chain_id):
    resp = await server.getConsensusNodes(chain_id,1,1000,0)
    nodes = resp['list']
    return nodes

async def process_block_height(server, chain_id, height,
                               big_batch, batch_blocks, batch_transactions):
    LOGGER.info("Synchronizing block #%d" % height)
    try:
        block = await request_block(server, chain_id, height=height)
        # if we are working on a big batch, don't save in db yet
        # add to a big dict instead
        await store_block(block, big_batch=big_batch,
                            batch_blocks=batch_blocks,
                            batch_transactions=batch_transactions)
        
        try:
            await do_block_postprocess(block, in_batch=big_batch)
        except:
            LOGGER.exception("Error in block postprocess")
    except ProtocolError:
        if big_batch:
            LOGGER.exception("Can't get height %d!!!!!!" % height)
        else:
            raise

async def check_blocks():
    from .jobs import update_missing_join
    chain_id = app['config'].nuls.chain_id.value
    
    last_stored_height = await get_last_block_height(chain_id=chain_id)
    last_height = -1
    if last_stored_height is None:
        last_stored_height = -1

    big_batch = False
    LOGGER.info("Last stored block is #%d" % last_stored_height)
    while True:
        server = await get_server()
        try:
            last_height = await request_last_height(server, chain_id)
            LOGGER.debug("Last upstream block is #%d" % last_height)
            big_batch = False
            if (last_height - last_stored_height) > 100:
                big_batch = True
            if last_height > last_stored_height:
                consensus_nodes = await request_consensus(server, chain_id)
                await Consensus.collection.replace_one(
                    {'height': last_height,
                     'chainId': chain_id},
                    {'height': last_height,
                     'agents': consensus_nodes,
                     'chainId': chain_id},
                     upsert=True)
 
                batch_blocks = dict()
                batch_transactions = dict()
                
                tasks = list()

                for i, block_height in enumerate(range(last_stored_height+1, last_height+1)):
                    task = process_block_height(server, chain_id, block_height,
                               big_batch, batch_blocks, batch_transactions)
                    if big_batch:
                        tasks.append(task)
                    else:
                        await task
                    
                    last_stored_height = block_height

                    if i > 10000:
                        break

                if big_batch:
                    await asyncio.gather(*tasks)
                    await model.db.blocks.insert_many(
                        sorted(batch_blocks.values(),
                               key=operator.itemgetter('height')))
                    await model.db.transactions.insert_many(
                        sorted(batch_transactions.values(),
                               key=operator.itemgetter('height')))
            
                    try:
                        await do_batch_postprocess(batch_blocks, batch_transactions)
                    except:
                        LOGGER.exception("Error in batch postprocess")
                        
        except:
            LOGGER.exception("Error in sync")
            last_stored_height = await get_last_block_height(chain_id=chain_id)
        finally:
            await server.session.close()
            
        if not big_batch:
            # we sleep only if we are not in the middle of a big batch
            await asyncio.sleep(8)

async def worker():
    while True:
        try:
            await check_blocks()
        except:
            LOGGER.exception("ERROR, relaunching in 10 seconds")
            await asyncio.sleep(10)

def start_connector():
    loop = asyncio.get_event_loop()
    loop.create_task(worker())
