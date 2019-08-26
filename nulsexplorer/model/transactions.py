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
               Index([("time", pymongo.DESCENDING)]),
               Index("type"),
               Index("outputs.address"),
               Index("inputs.address"),
               #Index("outputs.status"),
               #Index("outputs.lockTime"),
               Index("info.createTxHash"),
               Index("info.agentHash"),
               Index("info.contractAddress"),
               Index("info.result.success"),
               Index("info.aggregate.key"),
               Index("info.type"),
               Index("info.post.type"),
               Index("info.post.ref"),
               Index("info.post.content.tags"),
               Index("info.result.tokenTransfers.from"),
               Index("info.result.tokenTransfers.to"),
               Index([("time", pymongo.DESCENDING),
                      ("type", pymongo.ASCENDING)]),
               #Index([("outputs.status", pymongo.ASCENDING),
               #       ("outputs.lockTime", pymongo.ASCENDING)]),
               Index([("outputs.status", pymongo.DESCENDING),
                      ("outputs.lockTime", pymongo.ASCENDING)]),
               Index([("type", pymongo.ASCENDING),
                      ("inputs.address", pymongo.ASCENDING)]),
               Index([("type", pymongo.ASCENDING),
                      ("outputs.address", pymongo.ASCENDING)]),
               Index([("outputs.address", pymongo.ASCENDING),
                      ("outputs.status", pymongo.DESCENDING)])]

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
