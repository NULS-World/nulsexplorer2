from nulsexplorer.modules.register import register_tx_processor

import struct
import logging
import aiohttp # for now.
LOGGER = logging.getLogger('contract_module')


# async def process_contract_data(tx):
#     # This function takes a tx object and modifies it in place.
#     # we assume we have access to a config since we are in a processor
#     from nulsexplorer.main import api_request
#     async with aiohttp.ClientSession() as session:
#         LOGGER.info("Retrieving contract result for TX %s" % str(tx.hash))
#         result = await api_request(session, 'contract/result/%s' % str(tx.hash))
#         if result is None:
#             LOGGER.warning("Can't get contract info for TX %s" % str(tx.hash))

#         if result.get('flag', False):
#             tx.module_data['result'] = result['data']

#             if tx.type == 100: # contract creation
#                 contract_address = tx.module_data['result'].get('contractAddress')
#                 if contract_address is not None:
#                     LOGGER.info("Retrieving contract details for %s" % contract_address)
#                     result = await api_request(session, 'contract/info/%s' % contract_address)
#                     if result is None:
#                         LOGGER.warning("Can't get contract details for %s" % contract_address)
#                     else:
#                         print(repr(result))
#                         tx.module_data['details'] = result

#                 else:
#                     LOGGER.warning("Can't get contract details for %s" % contract_address)
#         else:
#             LOGGER.warning("Can't get contract info for TX %s" % str(tx.hash))

# register_tx_processor(process_contract_data, tx_types=[100,101,102,103], step="pre")
