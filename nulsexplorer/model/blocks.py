from nulsexplorer import model
from nulsexplorer.model.base import BaseClass, Index
from nulsexplorer.model.transactions import Transaction
import pymongo
import logging
import operator
LOGGER = logging.getLogger('model.blocks')

async def store_block(block_data, big_batch=False,
                      batch_blocks=None, batch_transactions=None):
    txs = block_data.pop("txList")
    if batch_transactions is None:
        batch_transactions = dict()

    for tx in txs:
        batch_transactions[tx['hash']] = tx
    #itxs = dict(zip(map(operator.itemgetter("hash"), txs), txs))

    if len(txs):
        #for transaction in txs:
        #    await Transaction.input_txdata(transaction)
        try:
            ntxs = list()
            for transaction in txs:
                transaction['chainId'] = block_data['header']['chainId']
                ntxs.append(
                    await Transaction.input_txdata(transaction, batch_mode=True,
                                                   batch_transactions=batch_transactions)
                    )
            if not big_batch:
                await model.db.transactions.insert_many(txs)
        except:
            LOGGER.exception("woops")
            if not big_batch:
                for transaction in txs:
                    await Transaction.input_txdata(transaction)

    if not big_batch:
        doc_id = await model.db.blocks.insert_one(block_data['header'])
        # for now we forget about bulk insert as we have to do some work on it...
        # await model.db.transactions.insert_many(txs)
        return doc_id
    else:
        batch_blocks[block_data['header']['hash']] = block_data['header']

async def get_last_block(chain_id, projection=None):
    query = model.db.blocks.find({
        "chainId": chain_id}, projection=projection).sort([('height', -1)]).limit(1)
    if await query.fetch_next:
        return query.next_object()
    else:
        return None

async def get_last_block_height(chain_id=None):
    if chain_id is None:
        from nulsexplorer.web import app
        chain_id = app['config'].nuls.chain_id.value
        
    block = await get_last_block(chain_id, projection={'height': 1})
    if block is not None:
        return block['height']
    else:
        return None

async def find_block(query):
    return await model.db.blocks.find_one(query)

async def find_blocks(query, scrubbed=True, sort=None, limit=0):
    projection = None
    if scrubbed:
        projection = {'height':1,
                      'hash': 1,
                      'preHash': 1,
                      'txCount': 1,
                      'createTime': 1,
                      'packingAddress': 1,
                      'agentHash': 1,
                      'agentId': 1,
                      'agentAlias': 1,
                      'reward': 1,
                      'fee': 1,
                      'size': 1,
                      'scriptSign': 1,
                      'seedPacked': 1,
                      'agentVersion': 1}
    if sort is None:
        sort = [('height', 1)]

    return model.db.blocks.find(query, projection=projection, limit=limit).sort(sort)

class Block(BaseClass):
    COLLECTION = "blocks"

    INDEXES = [Index("hash", unique=True),
               Index("height", pymongo.ASCENDING, unique=True),
               Index("height", pymongo.DESCENDING),
               Index("packingAddress")]
