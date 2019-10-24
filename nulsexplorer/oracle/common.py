from aleph_client.asynchronous import create_post, create_aggregate
from aleph_client.chains.nuls2 import NULSAccount, get_fallback_account
from logging import getLogger
LOGGER = getLogger("oracle.common")

async def get_account(config):
    account = None
    if config.aleph_client.private_key.value is not None:
        account = NULSAccount(
            private_key=bytes.fromhex(config.aleph_client.private_key.value),
            chain_id=config.nuls.chain_id.value)
    else:
        account = get_fallback_account(chain_id=config.nuls.chain_id.value)
    return account

async def get_channel(config):
    return config.aleph_client.channel.value

async def get_api_server(config):
    return config.aleph_client.api_server.value

async def broadcast_event(event_info, event_type, config=None):
    if config is None:
        from nulsexplorer.web import app
        config = app['config']
    
    account = await get_account(config)
    post_content = {
        'type': event_type,
        **event_info
    }
    post = await create_post(account, post_content, "NULS_EVENT",
                             channel=await get_channel(config),
                             api_server=await get_api_server(config))
    return post

async def submit_aggregate(key, content, config=None):
    if config is None:
        from nulsexplorer.web import app
        config = app['config']
        
    return await create_aggregate(
        await get_account(config), key, content,
        channel=await get_channel(config),
        api_server=await get_api_server(config))