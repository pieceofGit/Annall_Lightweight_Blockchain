import pytest
import sys
import os, sys


sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from blockchain import Block
from blockchain import Chain


class TestBlockchain:
    # Test that it generates exactly one genesis block

    def test_1(self):
        chain = Chain()
        assert isinstance(chain.get_genesis_block(), Block)
        assert len(chain.blocks) == 1

    # Test that the genesis block is in the correct format
    def test_2(self):
        chain = Chain()
        genesis_block = chain.get_genesis_block()
        assert (
            genesis_block.prev_hash == -1
            and genesis_block.coordinatorID == -1
            and genesis_block.payload == "genesis block"
            and genesis_block.writer_signature == -1
        )

    # Test that a block is added using the add_block function
    def test_3(self):
        chain = Chain()
        payload = "test payload"
        writer_id = 56
        coordinator_id = 89
        writer_signature = "Test signature"
        chain.add_block(payload, writer_id, writer_signature, coordinator_id)
        assert len(chain.blocks) == 2

    # Test that a block is created correctly using the add_block function
    def test_4(self):
        chain = Chain()
        payload = "test payload"
        writer_id = 56
        coordinator_id = 89
        writer_signature = "Test signature"
        chain.add_block(payload, writer_id, writer_signature, coordinator_id)
        block = Block(
            chain.get_genesis_block().hash,
            writer_id,
            coordinator_id,
            payload,
            writer_signature,
        )
        assert chain.blocks[1].hash == block.hash

    # Test that hashing is unique
    def test_5(self):
        chain = Chain()
        payload = "test payload"
        writer_id = 56
        coordinator_id = 89
        writer_signature = "Test signature"
        chain.add_block(payload, writer_id, writer_signature, coordinator_id)
        block = Block(
            chain.get_genesis_block().hash, writer_id, 90, payload, writer_signature,
        )
        assert chain.blocks[1].hash != block.hash

    # Test that the get_chain_payload function returns correct length
    def test_6(self):
        chain = Chain()
        payload = "test payload"
        writer_id = 56
        coordinator_id = 89
        writer_signature = "Test signature"
        for i in range(4):
            chain.add_block(payload, writer_id, writer_signature, coordinator_id)
        assert len(chain.get_chain_payload()) == 5

    # Test that hashing is unique if same block added multiple times
    def test_7(self):
        chain = Chain()
        payload = "test payload"
        writer_id = 56
        coordinator_id = 89
        writer_signature = "Test signature"
        for i in range(10):
            chain.add_block(payload, writer_id, writer_signature, coordinator_id)
        for h in chain.get_chain_hash():
            assert h.hash != h.prev_hash

