from nulsexplorer.modules.register import register_block_hook, register_batch_hook
from nulsexplorer.model.transactions import Transaction
from .common import broadcast_event, submit_aggregate
from logging import getLogger
LOGGER = getLogger("oracle.jobs")

async def block_event(block):
    await broadcast_event({
        'block': block
    }, 'new_block')
    
register_block_hook(block_event, also_in_batches=False)

async def nrc20_transfer_event(block):
    for transaction in block['txList']:
        if transaction.get('type') in [1,2]:
            continue
        transfers = transaction.get('txData', dict())\
            .get('resultInfo', dict())\
            .get('tokenTransfers', list())
            
        if len(transfers):
            await broadcast_event({
                'transaction': transaction
            }, 'token_transfer')
            
            for addr in set([t['contractAddress'] for t in transfers]):
                await update_nrc20_holders(addr)
    
register_block_hook(block_event, also_in_batches=False)

async def update_nrc20_holders(contract_address):
    from nulsexplorer.web.controllers.contracts import get_holders
    
    LOGGER.info(f"Updating balances of f{contract_address}")
    
    create_tx = await Transaction.collection.find_one({
        'type': 15,
        'txData.contractAddress': contract_address
    })
    if not create_tx:
        LOGGER.warning(f"Can't find creation tx for contract {contract_address}")
        return
    
    holders = await get_holders(contract_address)
    if len(holders):
        contract_info = {
            'holders': {h['_id']: h['balance'] for h in holders},
            'alias': create_tx['txData'].get('alias'),
            'symbol': create_tx['txData'].get('symbol'),
            'decimals': create_tx['txData'].get('decimals'),
            'token_name': create_tx['txData'].get('tokenName'),
            'creation_block_height': create_tx['txData'].get('blockHeight'),
            'total_supply': create_tx['txData'].get('totalSupply')
        }
        await submit_aggregate(f"contract_{contract_address}",
                               contract_info)

async def update_batch_nrc20_holders(batch_blocks, batch_transactions):
    updated_contracts = set()
    for transaction in batch_transactions.values():
        if transaction.get('type') in [1,2]:
            continue
        
        txData = transaction.get('txData', None)
        if txData is None:
            continue
        
        resultInfo = txData.get('resultInfo', None)
        if resultInfo is None:
            continue
        
        transfers = resultInfo.get('tokenTransfers', None)
            
        if transfers is not None and len(transfers):
            for addr in set([t['contractAddress'] for t in transfers]):
                updated_contracts.add(addr)
                
    if updated_contracts:
        LOGGER.info(f"Updated contracts: {repr(updated_contracts)}")
        for contract_address in updated_contracts:
            await update_nrc20_holders(contract_address)
    
register_batch_hook(update_batch_nrc20_holders)