from logging import getLogger
import aiocron
import asyncio
from datetime import date, time, timezone, datetime, timedelta
from nulsexplorer.modules.register import register_batch_hook, register_block_hook

LOGGER = getLogger("JOBS")

@aiocron.crontab('*/30 * * * *', start=False)
async def update_addresses_balances():
    from nulsexplorer.model.blocks import get_last_block_height
    from nulsexplorer.web.controllers.addresses import addresses_unspent_txs
    LOGGER.info("updating addresses balances")
    last_block = await get_last_block_height()
    unspent = await addresses_unspent_txs(last_block, output_collection="cached_unspent")
    await asyncio.sleep(0)
    
async def update_leave_tx(tx_info):
    from nulsexplorer.model.transactions import Transaction
    nonce = tx_info['coinFroms'][0]['nonce']
    amount = tx_info['coinFroms'][0]['amount']
    address = tx_info['coinFroms'][0]['address']
    async for tx in Transaction.collection.find({
        'coinTos': {
            "$elemMatch": {
                "address": address,
                "lockTime": -1,
                "amount": amount
            }}}, projection=['hash', 'txData.agentHash']):
        if not tx['hash'].endswith(nonce):
            continue
            
        await Transaction.collection.update_one({
            'hash': tx_info['hash']
        }, {
            '$set': {
                "txData.amount": amount,
                "txData.agentHash": tx['txData']['agentHash'],
                "txData.address": address
            }
        })
    
async def update_missing_join(*args, **kwargs):
    from nulsexplorer.model.transactions import Transaction
    filters = {
        'type': 6, # TODO: handle other consensus leave (unregister, red card...)
        'txData.agentHash': None}
    count = await Transaction.collection.count_documents(filters)
    if count:
        LOGGER.info("Updating missing join %d txs" % count)
        async for tx in Transaction.collection.find(filters, projection=['hash', 'coinFroms']):
            await update_leave_tx(tx)

register_batch_hook(update_missing_join)
register_block_hook(update_missing_join, also_in_batches=False)

def start_jobs():
    update_addresses_balances.start()
