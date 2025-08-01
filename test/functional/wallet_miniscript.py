#!/usr/bin/env python3
# Copyright (c) 2022 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Test Miniscript descriptors integration in the wallet."""

from test_framework.descriptors import descsum_create
from test_framework.psbt import PSBT, PSBT_IN_SHA256
from test_framework.test_framework import KingpepeTestFramework
from test_framework.util import assert_equal


TPRVS = [
    "tprv8ZgxMBicQKsPerQj6m35no46amfKQdjY7AhLnmatHYXs8S4MTgeZYkWAn4edSGwwL3vkSiiGqSZQrmy5D3P5gBoqgvYP2fCUpBwbKTMTAkL",
    "tprv8ZgxMBicQKsPd3cbrKjE5GKKJLDEidhtzSSmPVtSPyoHQGL2LZw49yt9foZsN9BeiC5VqRaESUSDV2PS9w7zAVBSK6EQH3CZW9sMKxSKDwD",
    "tprv8iF7W37EHnVEtDr9EFeyFjQJFL6SfGby2AnZ2vQARxTQHQXy9tdzZvBBVp8a19e5vXhskczLkJ1AZjqgScqWL4FpmXVp8LLjiorcrFK63Sr",
]
TPUBS = [
    "tpubD6NzVbkrYhZ4YPAbyf6urxqqnmJF79PzQtyERAmvkSVS9fweCTjxjDh22Z5St9fGb1a5DUCv8G27nYupKP1Ctr1pkamJossoetzws1moNRn",
    "tpubD6NzVbkrYhZ4YMQC15JS7QcrsAyfGrGiykweqMmPxTkEVScu7vCZLNpPXW1XphHwzsgmqdHWDQAfucbM72EEB1ZEyfgZxYvkZjYVXx1xS9p",
    "tpubD6NzVbkrYhZ4YU9vM1s53UhD75UyJatx8EMzMZ3VUjR2FciNfLLkAw6a4pWACChzobTseNqdWk4G7ZdBqRDLtLSACKykTScmqibb1ZrCvJu",
    "tpubD6NzVbkrYhZ4XRMcMFMMFvzVt6jaDAtjZhD7JLwdPdMm9xa76DnxYYP7w9TZGJDVFkek3ArwVsuacheqqPog8TH5iBCX1wuig8PLXim4n9a",
    "tpubD6NzVbkrYhZ4WsqRzDmkL82SWcu42JzUvKWzrJHQ8EC2vEHRHkXj1De93sD3biLrKd8XGnamXURGjMbYavbszVDXpjXV2cGUERucLJkE6cy",
    "tpubDEFLeBkKTm8aiYkySz8hXAXPVnPSfxMi7Fxhg9sejUrkwJuRWvPdLEiXjTDbhGbjLKCZUDUUibLxTnK5UP1q7qYrSnPqnNe7M8mvAW1STcc",
]
PUBKEYS = [
    "02aebf2d10b040eb936a6f02f44ee82f8b34f5c1ccb20ff3949c2b28206b7c1068",
    "030f64b922aee2fd597f104bc6cb3b670f1ca2c6c49b1071a1a6c010575d94fe5a",
    "02abe475b199ec3d62fa576faee16a334fdb86ffb26dce75becebaaedf328ac3fe",
    "0314f3dc33595b0d016bb522f6fe3a67680723d842c1b9b8ae6b59fdd8ab5cccb4",
    "025eba3305bd3c829e4e1551aac7358e4178832c739e4fc4729effe428de0398ab",
    "029ffbe722b147f3035c87cb1c60b9a5947dd49c774cc31e94773478711a929ac0",
    "0211c7b2e18b6fd330f322de087da62da92ae2ae3d0b7cec7e616479cce175f183",
]

MINISCRIPTS = [
    # One of two keys
    f"or_b(pk({TPUBS[0]}/*),s:pk({TPUBS[1]}/*))",
    # A script similar (same spending policy) to BOLT3's offered HTLC (with anchor outputs)
    f"or_d(pk({TPUBS[0]}/*),and_v(and_v(v:pk({TPUBS[1]}/*),or_c(pk({TPUBS[2]}/*),v:hash160(7f999c905d5e35cefd0a37673f746eb13fba3640))),older(1)))",
    # A Revault Unvault policy with the older() replaced by an after()
    f"andor(multi(2,{TPUBS[0]}/*,{TPUBS[1]}/*),and_v(v:multi(4,{PUBKEYS[0]},{PUBKEYS[1]},{PUBKEYS[2]},{PUBKEYS[3]}),after(424242)),thresh(4,pkh({TPUBS[2]}/*),a:pkh({TPUBS[3]}/*),a:pkh({TPUBS[4]}/*),a:pkh({TPUBS[5]}/*)))",
    # Liquid-like federated pegin with emergency recovery keys
    f"or_i(and_b(pk({PUBKEYS[0]}),a:and_b(pk({PUBKEYS[1]}),a:and_b(pk({PUBKEYS[2]}),a:and_b(pk({PUBKEYS[3]}),s:pk({PUBKEYS[4]}))))),and_v(v:thresh(2,pkh({TPUBS[0]}/*),a:pkh({PUBKEYS[5]}),a:pkh({PUBKEYS[6]})),older(4209713)))",
]

MINISCRIPTS_PRIV = [
    # One of two keys, of which one private key is known
    {
        "ms": f"or_i(pk({TPRVS[0]}/*),pk({TPUBS[0]}/*))",
        "sequence": None,
        "locktime": None,
        "sigs_count": 1,
        "stack_size": 3,
    },
    # A more complex policy, that can't be satisfied through the first branch (need for a preimage)
    {
        "ms": f"andor(ndv:older(2),and_v(v:pk({TPRVS[0]}),sha256(2a8ce30189b2ec3200b47aeb4feaac8fcad7c0ba170389729f4898b0b7933bcb)),and_v(v:pkh({TPRVS[1]}),pk({TPRVS[2]}/*)))",
        "sequence": 2,
        "locktime": None,
        "sigs_count": 3,
        "stack_size": 5,
    },
    # The same policy but we provide the preimage. This path will be chosen as it's a smaller witness.
    {
        "ms": f"andor(ndv:older(2),and_v(v:pk({TPRVS[0]}),sha256(61e33e9dbfefc45f6a194187684d278f789fd4d5e207a357e79971b6519a8b12)),and_v(v:pkh({TPRVS[1]}),pk({TPRVS[2]}/*)))",
        "sequence": 2,
        "locktime": None,
        "sigs_count": 3,
        "stack_size": 4,
        "sha256_preimages": {
            "61e33e9dbfefc45f6a194187684d278f789fd4d5e207a357e79971b6519a8b12": "e8774f330f5f330c23e8bbefc5595cb87009ddb7ac3b8deaaa8e9e41702d919c"
        },
    },
    # Signature with a relative timelock
    {
        "ms": f"and_v(v:older(2),pk({TPRVS[0]}/*))",
        "sequence": 2,
        "locktime": None,
        "sigs_count": 1,
        "stack_size": 2,
    },
    # Signature with an absolute timelock
    {
        "ms": f"and_v(v:after(20),pk({TPRVS[0]}/*))",
        "sequence": None,
        "locktime": 20,
        "sigs_count": 1,
        "stack_size": 2,
    },
    # Signature with both
    {
        "ms": f"and_v(v:older(4),and_v(v:after(30),pk({TPRVS[0]}/*)))",
        "sequence": 4,
        "locktime": 30,
        "sigs_count": 1,
        "stack_size": 2,
    },
    # We have one key on each branch; Core signs both (can't finalize)
    {
        "ms": f"c:andor(pk({TPRVS[0]}/*),pk_k({TPUBS[0]}),and_v(v:pk({TPRVS[1]}),pk_k({TPUBS[1]})))",
        "sequence": None,
        "locktime": None,
        "sigs_count": 2,
        "stack_size": None,
    },
    # We have all the keys, wallet selects the timeout path to sign since it's smaller and sequence is set
    {
        "ms": f"andor(pk({TPRVS[0]}/*),pk({TPRVS[2]}),and_v(v:pk({TPRVS[1]}),older(10)))",
        "sequence": 10,
        "locktime": None,
        "sigs_count": 3,
        "stack_size": 3,
    },
    # We have all the keys, wallet selects the primary path to sign unconditionally since nsequence wasn't set to be valid for timeout path
    {
        "ms": f"andor(pk({TPRVS[0]}/*),pk({TPRVS[2]}),and_v(v:pkh({TPRVS[1]}),older(10)))",
        "sequence": None,
        "locktime": None,
        "sigs_count": 3,
        "stack_size": 3,
    },
    # Finalizes to the smallest valid witness, regardless of sequence
    {
        "ms": f"or_d(pk({TPRVS[0]}/*),and_v(v:pk({TPRVS[1]}),and_v(v:pk({TPRVS[2]}),older(10))))",
        "sequence": 12,
        "locktime": None,
        "sigs_count": 3,
        "stack_size": 2,
    },
    # Liquid-like federated pegin with emergency recovery privkeys
    {
        "ms": f"or_i(and_b(pk({TPUBS[0]}/*),a:and_b(pk({TPUBS[1]}),a:and_b(pk({TPUBS[2]}),a:and_b(pk({TPUBS[3]}),s:pk({PUBKEYS[0]}))))),and_v(v:thresh(2,pkh({TPRVS[0]}),a:pkh({TPRVS[1]}),a:pkh({TPUBS[4]})),older(42)))",
        "sequence": 42,
        "locktime": None,
        "sigs_count": 2,
        "stack_size": 8,
    },
]


class WalletMiniscriptTest(KingpepeTestFramework):
    def add_options(self, parser):
        self.add_wallet_options(parser, legacy=False)

    def set_test_params(self):
        self.num_nodes = 1

    def skip_test_if_missing_module(self):
        self.skip_if_no_wallet()
        self.skip_if_no_sqlite()

    def watchonly_test(self, ms):
        self.log.info(f"Importing Miniscript '{ms}'")
        desc = descsum_create(f"wsh({ms})")
        assert self.ms_wo_wallet.importdescriptors(
            [
                {
                    "desc": desc,
                    "active": True,
                    "range": 2,
                    "next_index": 0,
                    "timestamp": "now",
                }
            ]
        )[0]["success"]

        self.log.info("Testing we derive new addresses for it")
        assert_equal(
            self.ms_wo_wallet.getnewaddress(), self.funder.deriveaddresses(desc, 0)[0]
        )
        assert_equal(
            self.ms_wo_wallet.getnewaddress(), self.funder.deriveaddresses(desc, 1)[1]
        )

        self.log.info("Testing we detect funds sent to one of them")
        addr = self.ms_wo_wallet.getnewaddress()
        txid = self.funder.sendtoaddress(addr, 0.01)
        self.wait_until(
            lambda: len(self.ms_wo_wallet.listunspent(minconf=0, addresses=[addr])) == 1
        )
        utxo = self.ms_wo_wallet.listunspent(minconf=0, addresses=[addr])[0]
        assert utxo["txid"] == txid and utxo["solvable"]

    def signing_test(
        self, ms, sequence, locktime, sigs_count, stack_size, sha256_preimages
    ):
        self.log.info(f"Importing private Miniscript '{ms}'")
        desc = descsum_create(f"wsh({ms})")
        res = self.ms_sig_wallet.importdescriptors(
            [
                {
                    "desc": desc,
                    "active": True,
                    "range": 0,
                    "next_index": 0,
                    "timestamp": "now",
                }
            ]
        )
        assert res[0]["success"], res

        self.log.info("Generating an address for it and testing it detects funds")
        addr = self.ms_sig_wallet.getnewaddress()
        txid = self.funder.sendtoaddress(addr, 0.01)
        self.wait_until(lambda: txid in self.funder.getrawmempool())
        self.funder.generatetoaddress(1, self.funder.getnewaddress())
        utxo = self.ms_sig_wallet.listunspent(addresses=[addr])[0]
        assert txid == utxo["txid"] and utxo["solvable"]

        self.log.info("Creating a transaction spending these funds")
        dest_addr = self.funder.getnewaddress()
        seq = sequence if sequence is not None else 0xFFFFFFFF - 2
        lt = locktime if locktime is not None else 0
        psbt = self.ms_sig_wallet.createpsbt(
            [
                {
                    "txid": txid,
                    "vout": utxo["vout"],
                    "sequence": seq,
                }
            ],
            [{dest_addr: 0.009}],
            lt,
        )

        self.log.info("Signing it and checking the satisfaction.")
        if sha256_preimages is not None:
            psbt = PSBT.from_base64(psbt)
            for (h, preimage) in sha256_preimages.items():
                k = PSBT_IN_SHA256.to_bytes(1, "big") + bytes.fromhex(h)
                psbt.i[0].map[k] = bytes.fromhex(preimage)
            psbt = psbt.to_base64()
        res = self.ms_sig_wallet.walletprocesspsbt(psbt=psbt, finalize=False)
        psbtin = self.nodes[0].rpc.decodepsbt(res["psbt"])["inputs"][0]
        assert len(psbtin["partial_signatures"]) == sigs_count
        res = self.ms_sig_wallet.finalizepsbt(res["psbt"])
        assert res["complete"] == (stack_size is not None)

        if stack_size is not None:
            txin = self.nodes[0].rpc.decoderawtransaction(res["hex"])["vin"][0]
            assert len(txin["txinwitness"]) == stack_size, txin["txinwitness"]
            self.log.info("Broadcasting the transaction.")
            # If necessary, satisfy a relative timelock
            if sequence is not None:
                self.funder.generatetoaddress(sequence, self.funder.getnewaddress())
            # If necessary, satisfy an absolute timelock
            height = self.funder.getblockcount()
            if locktime is not None and height < locktime:
                self.funder.generatetoaddress(
                    locktime - height, self.funder.getnewaddress()
                )
            self.ms_sig_wallet.sendrawtransaction(res["hex"])

    def run_test(self):
        self.log.info("Making a descriptor wallet")
        self.funder = self.nodes[0].get_wallet_rpc(self.default_wallet_name)
        self.nodes[0].createwallet(
            wallet_name="ms_wo", descriptors=True, disable_private_keys=True
        )
        self.ms_wo_wallet = self.nodes[0].get_wallet_rpc("ms_wo")
        self.nodes[0].createwallet(wallet_name="ms_sig", descriptors=True)
        self.ms_sig_wallet = self.nodes[0].get_wallet_rpc("ms_sig")

        # Sanity check we wouldn't let an insane Miniscript descriptor in
        res = self.ms_wo_wallet.importdescriptors(
            [
                {
                    "desc": descsum_create(
                        "wsh(and_b(ripemd160(1fd9b55a054a2b3f658d97e6b84cf3ee00be429a),a:1))"
                    ),
                    "active": False,
                    "timestamp": "now",
                }
            ]
        )[0]
        assert not res["success"]
        assert "is not sane: witnesses without signature exist" in res["error"]["message"]

        # Test we can track any type of Miniscript
        for ms in MINISCRIPTS:
            self.watchonly_test(ms)

        # Test we can sign for any Miniscript.
        for ms in MINISCRIPTS_PRIV:
            self.signing_test(
                ms["ms"],
                ms["sequence"],
                ms["locktime"],
                ms["sigs_count"],
                ms["stack_size"],
                ms.get("sha256_preimages"),
            )


if __name__ == "__main__":
    WalletMiniscriptTest().main()
