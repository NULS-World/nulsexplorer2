import asyncio
import aiohttp
import logging
import base64
import operator

from aiohttp import web, ClientSession
from jsonrpc_async import Server

from nulsexplorer.web import app
from nulsexplorer import model
from nulsexplorer.model.blocks import get_last_block_height, store_block
from nulsexplorer.model.transactions import Transaction
from nulsexplorer.model.consensus import Consensus

LOGGER = logging.getLogger('connector')

async def get_server():
    base_uri = app['config'].nuls.base_uri.value
    return Server(base_uri)

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
    block = await request_block(server, chain_id, height=height)
    # if we are working on a big batch, don't save in db yet
    # add to a big dict instead
    await store_block(block, big_batch=big_batch,
                        batch_blocks=batch_blocks,
                        batch_transactions=batch_transactions)

async def check_blocks():
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

                    if i > 1000:
                        break

                if big_batch:
                    await asyncio.gather(*tasks)
                    await model.db.blocks.insert_many(
                        sorted(batch_blocks.values(),
                               key=operator.itemgetter('height')))
                    await model.db.transactions.insert_many(
                        sorted(batch_transactions.values(),
                               key=operator.itemgetter('height')))
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
