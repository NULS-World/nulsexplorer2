# We will register here processors for the tx by types
# Pre-processor is before the insertion
TX_PREPROCESS_REGISTER = dict()

# Post-processor is after the insertion
TX_POSTPROCESS_REGISTER = dict()

BLOCK_POSTPROCESS_REGISTER = list()
BATCH_POSTPROCESS_REGISTER = list()

# We will register here handlers for the tx types
TX_TYPES_REGISTER = dict()

def register_tx_type(tx_types, handler_class):
    if not isinstance(tx_types, (list, tuple)):
        tx_types = [tx_types]

    for tx_type in tx_types:
        TX_TYPES_REGISTER[tx_type] = handler_class

def register_tx_processor(handler, tx_types=0, step = "pre"):
    if not isinstance(tx_types, (list, tuple)):
        tx_types = [tx_types]

    registry = TX_PREPROCESS_REGISTER
    if step == "post":
        registry = TX_POSTPROCESS_REGISTER

    for tx_type in tx_types:
        registry.setdefault(tx_type, []).append(handler)

async def process_tx(tx, step="pre"):
    registry = TX_PREPROCESS_REGISTER
    if step == "post":
        registry = TX_POSTPROCESS_REGISTER

    for handler in registry.setdefault(0, []):
        await handler(tx)

    for handler in registry.setdefault(tx.type, []):
        await handler(tx)
        
def register_batch_hook(handler):
    if handler not in BATCH_POSTPROCESS_REGISTER:
        BATCH_POSTPROCESS_REGISTER.append(handler)
        
async def do_batch_postprocess(batch_blocks, batch_transactions):
    for handler in BATCH_POSTPROCESS_REGISTER:
        await handler(batch_blocks, batch_transactions)

def register_block_hook(handler, also_in_batches=False):
    if (also_in_batches, handler) not in BLOCK_POSTPROCESS_REGISTER:
        BLOCK_POSTPROCESS_REGISTER.append((also_in_batches, handler))
        
async def do_block_postprocess(block, in_batch=True):
    for do_in_batch, handler in BLOCK_POSTPROCESS_REGISTER:
        if (not in_batch) or do_in_batch:
            await handler(block)