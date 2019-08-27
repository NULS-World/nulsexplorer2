import uvloop
uvloop.install()

TRANSACTION_TYPES = {
    1: "consensus reward",
    2: "transfer transaction",
    3: "set alias",
    4: "register consensus node",
    5: "join consensus",
    6: "cancel consensus",
    7: "yellow card",
    8: "red card",
    9: "unregister consensus node",
    10: "cross chain",
    11: "register chain",
    12: "destroy chain",
    13: "add asset to chain",
    14: "remove asset from chain",
    15: "create contract",
    16: "call contract",
    17: "delete contract",
    18: "transfer contract",
    19: "contract return gas",
    20: "contract register consensus node",
    21: "contract join consensus",
    22: "contract cancel consensus",
    23: "contract unregister consensus node"
}
