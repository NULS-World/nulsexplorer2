from aiohttp import web, ClientSession

from nulsexplorer.web import app
from nulsexplorer.model.transactions import Transaction
from nulsexplorer.model.blocks import (get_last_block_height)

from .utils import (Pagination, PER_PAGE, PER_PAGE_SUMMARY,
                    cond_output)

# async def get_contracts():
#     aggregate = Transaction.collection.aggregate([
#          {'$match': {'$and':
#             {'type': 100,
#              'info.result.success': True}}},
#          {'$sort': {'_id': 1}}])
#     return [item async for item in aggregate]

async def contracts_list(request):
    """ Contracts view
    """
    from nulsexplorer.model import db
    last_height = await get_last_block_height()
    page = int(request.match_info.get('page', '1'))
    only_tokens = bool(int(request.query.get('tokens', 0)))

    contracts_query = {
        'type': 15,
        'txData.resultInfo.success': True
    }
    sort = [('height', -1)]

    if (only_tokens):
        sort = [('txData.result.symbol', 1)]
        contracts_query.update({
            'txData.tokenName': {'$ne': None},
            'txData.symbol': {'$ne': None}
        })

    total_contracts = await Transaction.collection.count_documents(contracts_query)
    pagination = Pagination(page, PER_PAGE_SUMMARY, total_contracts)

    contract_creations = Transaction.collection.find(contracts_query,
                                                     sort=sort,
                                                     skip=(page-1)*PER_PAGE_SUMMARY,
                                                     limit=PER_PAGE_SUMMARY)

    page = int(request.match_info.get('page', '1'))
    contract_creations = [tx async for tx in contract_creations]

    context = {'contract_creations': contract_creations,
               'pagination': pagination,
               'last_height': last_height,
               'only_tokens': only_tokens,
               'pagination_page': page,
               'pagination_total': total_contracts,
               'pagination_per_page': PER_PAGE_SUMMARY,
               'pagination_item': 'contract_creations'}

    return cond_output(request, context, 'contracts.html')

app.router.add_get('/addresses/contracts', contracts_list)
app.router.add_get('/addresses/contracts.json', contracts_list)
app.router.add_get('/addresses/contracts/page/{page}', contracts_list)
app.router.add_get('/addresses/contracts/page/{page}.json', contracts_list)


async def get_holders(contract_address, pagination=False,
                      per_page=100, page=1):
    aggregate = [
        {'$match': {
            'txData.contractAddress': contract_address,
            'txData.resultInfo.tokenTransfers': {'$exists': True, '$ne': []}
        }},
        {'$unwind': '$txData.resultInfo.tokenTransfers'},
        {'$addFields': {
            'transfers': {'$concatArrays': [
            [['$txData.resultInfo.tokenTransfers.fromAddress',
                {'$toDouble': {"$concat": ["-", "$txData.resultInfo.tokenTransfers.value"]}}]],
            [['$txData.resultInfo.tokenTransfers.toAddress',
                {'$toDouble': "$txData.resultInfo.tokenTransfers.value"}]],
            ]}
            }},
        {'$unwind': '$transfers'},
        {'$project': {
            'transfers': 1
        }},
        # { "$group" : { "_id" : "$transfers.0", "balance" : { "$sum" : "$transfers.1" } } }
        {"$group": {
            "_id": {'$arrayElemAt': ["$transfers", 0]},
            "balance": {"$sum": {'$arrayElemAt': ["$transfers", 1]}}
            }},
        {'$match': {
            '_id': {'$ne': None}
        }},
        {'$sort': {'balance': -1}}
    ]
    if pagination:
        aggregate.extend([
            {'$skip': (page-1)*per_page},
            {'$limit': per_page}
        ])
    holders = Transaction.collection.aggregate(aggregate)
    holders = [b async for b in holders]
    return holders


async def view_contract(request):
    from .addresses import (addresses_unspent_info, summarize_tx)

    last_height = await get_last_block_height()

    address = request.match_info['address']
    mode = request.match_info.get('mode', 'summary')
    create_tx = await Transaction.collection.find_one({
        'type': 15,
        'txData.contractAddress': address
    })

    if create_tx is None:
        raise web.HTTPNotFound(text="Contract not found")

    page = int(request.match_info.get('page', '1'))
    per_page = PER_PAGE_SUMMARY
    pagination_item = 'transactions'

    where_query = {'$or':
                    [{'txData.contractAddress': address},
                     {'txFroms.address': address},
                     {'toTos.address': address}]}
    transactions = []
    pagination_count = 0
    holders = []
    if (mode in ['summary', 'calls-summary']):
        if mode == "calls-summary":
            where_query['type'] = 16
        transactions = [tx async for tx in
                        Transaction.collection.find(where_query,
                                                    sort=[('createTime', -1)],
                                                    limit=per_page,
                                                    skip=(page-1)*per_page)]
        pagination_count = await Transaction.count(where_query)

        transactions = [await summarize_tx(tx, address) for tx in transactions]

    if mode == "holders":
        pagination_item = 'holders'
        holders = await get_holders(address, pagination=True, per_page=per_page, page=page)

        total_count = Transaction.collection.aggregate([
            {'$match': {
                'txData.contractAddress': address,
                'txData.resultInfo.tokenTransfers': {'$exists': True, '$ne': []}
            }},
            {'$unwind': '$txData.resultInfo.tokenTransfers'},
            {"$group": {
                "_id": "$txData.resultInfo.tokenTransfers.toAddress"
            }},
            {'$group': {'_id': None, 'count':
                        {'$sum': 1}}}
        ])
        if await total_count.fetch_next:
            pagination_count = total_count.next_object()['count']

    elif mode == "transfer-summary":
        transactions = Transaction.collection.aggregate([
            {'$match': {
                'txData.contractAddress': address,
                'txData.resultInfo.tokenTransfers': {'$exists': True, '$ne': []}
            }},
            {'$unwind': '$txData.resultInfo.tokenTransfers'},
            {'$sort': {'createTime': -1}},
            {'$skip': (page-1)*per_page},
            {'$limit': per_page},
            {'$project': {
             'transfer': '$txData.resultInfo.tokenTransfers',
             'hash': 1,
             'blockHeight': 1,
             'fee': 1,
             'createTime': 1,
             'remark': 1,
             'gasUsed': '$txData.resultInfo.gasUsed',
             'price': '$txData.resultInfo.price',
             'totalFee': '$txData.resultInfo.totalFee',
             'nonce': '$txData.resultInfo.nonce'
             }}
        ])
        transactions = [b async for b in transactions]

        total_count = Transaction.collection.aggregate([
            {'$match': {
                'txData.contractAddress': address,
                'txData.resultInfo.tokenTransfers': {'$exists': True, '$ne': []}
            }},
            {'$group': {'_id': None, 'count':
                        {'$sum': {'$size': '$txData.resultInfo.tokenTransfers'}}}}
        ])
        if await total_count.fetch_next:
            pagination_count = total_count.next_object()['count']

    unspent_info = (await addresses_unspent_info(last_height,
                                                 address_list=[address])
                    ).get(address, {})

    pagination = Pagination(page, per_page, pagination_count)

    context = {'address': address,
               'create_tx': create_tx,
               'transactions': transactions,
               'holders': holders,
               'pagination': pagination,
               'last_height': last_height,
               'pagination_count': pagination_count,
               'mode': mode,
               'pagination_page': page,
               'pagination_total': pagination_count,
               'pagination_per_page': per_page,
               'pagination_item': pagination_item,
               'unspent_info': unspent_info}

    return cond_output(request, context, 'contract.html')

async def contract_methods(request):
    address = request.match_info['address']
    last_height = await get_last_block_height()
    async with ClientSession() as session:
        result = await api_request(session, 'contract/info/%s' % address)

    context = {'address': address,
               'methods': result['method']}

    return cond_output(request, context, 'api.html')


app.router.add_get('/addresses/contracts/{address}/methods.json', contract_methods)

async def contract_call(request):
    data = await request.json()

    async with ClientSession() as session:
        output = await api_post(session,
                                'contract/view',
                                data)

    return web.json_response(output)

app.router.add_post('/addresses/contracts/call', contract_call)

app.router.add_get('/addresses/contracts/{address}.json', view_contract)
app.router.add_get('/addresses/contracts/{address}', view_contract)
app.router.add_get('/addresses/contracts/{address}/{mode}.json', view_contract)
app.router.add_get('/addresses/contracts/{address}/{mode}', view_contract)
app.router.add_get('/addresses/contracts/{address}/page/{page}.json', view_contract)
app.router.add_get('/addresses/contracts/{address}/page/{page}', view_contract)
app.router.add_get('/addresses/contracts/{address}/{mode}/page/{page}.json', view_contract)
app.router.add_get('/addresses/contracts/{address}/{mode}/page/{page}', view_contract)
