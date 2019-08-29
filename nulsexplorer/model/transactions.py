""" Transactions are generated from the block content.
"""

import pymongo
from nulsexplorer.model.base import BaseClass, Index
from pymongo import UpdateOne

import logging
import operator
LOGGER = logging.getLogger('model.transactions')

class Transaction(BaseClass):
    COLLECTION = "transactions"

    INDEXES = [Index("hash", unique=True),
               Index([("height", pymongo.ASCENDING)]),
               Index([("height", pymongo.DESCENDING)]),
               Index([("createTime", pymongo.DESCENDING)]),
               Index("type"),
               Index("coinFroms.address"),
               Index("coinTos.address"),
               #Index("outputs.status"),
               #Index("outputs.lockTime"),
               Index("txData.createTxHash"),
               Index("txData.agentHash"),
               Index("txData.contractAddress"),
               Index("txData.result.success"),
               Index("txData.aggregate.key"),
               Index("txData.type"),
               Index("txData.resultInfo.tokenTransfers.fromAddress"),
               Index("txData.resultInfo.tokenTransfers.toAddress"),
               Index([("createTime", pymongo.DESCENDING),
                      ("type", pymongo.ASCENDING)])]

    @classmethod
    async def input_txdata(cls, tx_data, batch_mode=False,
                           batch_transactions=None):
        #await cls.collection.insert(tx_data)
        transaction = tx_data
        collec = cls.collection

        # if transaction['type'] == 6:
        #     join_tx_hash = transaction['info'].get('joinTxHash', None)
        #     if join_tx_hash is not None:
        #         if batch_mode and (join_tx_hash in batch_transactions):
        #             join_tx = batch_transactions[join_tx_hash]
        #         else:
        #             join_tx = await collec.find_one(dict(hash=join_tx_hash))
        #         transaction['info']['address'] = join_tx['info']['address']
        #         transaction['info']['agentHash'] = join_tx['info']['agentHash']
                
        if batch_mode:
            return transaction
        else:
            try:
                await collec.insert_one(tx_data)
            except pymongo.errors.DuplicateKeyError:
                LOGGER.warning("Transaction %s was already there" % transaction['hash'])
