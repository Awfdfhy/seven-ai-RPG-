"""
RPG-10-07: Economy System Tests
Tests for merchants, price rules, market trends, transactions, and trading.

Run with: python -m pytest tests/test_economy.py -v
or:       python tests/test_economy.py
"""

from __future__ import annotations

import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from economy import (
    EconomyManager,
    MarketState,
    MerchantDefinition,
    MerchantType,
    PriceRule,
    Transaction,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager() -> EconomyManager:
    mgr = EconomyManager()
    mgr.load_merchants([
        MerchantDefinition(
            id="blacksmith_01",
            name="Grimjaw Smithy",
            merchant_type=MerchantType.BLACKSMITH,
            region_id="oakhaven_region",
            location_id="oakhaven",
            description="A sturdy smithy.",
            buy_markup=1.2,
            sell_discount=0.4,
        ),
        MerchantDefinition(
            id="alchemist_01",
            name="Whispering Vials",
            merchant_type=MerchantType.ALCHEMIST,
            region_id="oakhaven_region",
            location_id="oakhaven",
            description="An alchemical shop.",
            buy_markup=1.1,
            sell_discount=0.5,
        ),
        MerchantDefinition(
            id="general_01",
            name="Traveling Merchant",
            merchant_type=MerchantType.GENERAL,
            region_id="frostveil_peaks",
            location_id="frostveil_pass",
            description="A wandering trader.",
            buy_markup=1.3,
            sell_discount=0.3,
        ),
    ])
    mgr.load_price_rules("blacksmith_01", [
        PriceRule(item_id="iron_sword", base_price=50, min_price=20, max_price=200),
        PriceRule(item_id="iron_ingot", base_price=10, min_price=2, max_price=50),
    ])
    mgr.load_price_rules("alchemist_01", [
        PriceRule(item_id="healing_potion", base_price=25, min_price=5, max_price=100),
        PriceRule(item_id="mana_potion", base_price=30, min_price=5, max_price=100),
    ])
    mgr.load_price_rules("general_01", [
        PriceRule(item_id="rope", base_price=5, min_price=1, max_price=20),
        PriceRule(item_id="torch", base_price=2, min_price=1, max_price=10),
    ])
    return mgr


# ---------------------------------------------------------------------------
# MerchantDefinition tests
# ---------------------------------------------------------------------------

class TestMerchantDefinition(unittest.TestCase):
    def test_from_dict(self):
        data = {
            "id": "m1",
            "name": "Test Merchant",
            "merchant_type": "blacksmith",
            "region_id": "r1",
            "location_id": "l1",
            "buy_markup": 1.5,
            "sell_discount": 0.6,
        }
        m = MerchantDefinition.from_dict(data)
        assert m.id == "m1"
        assert m.name == "Test Merchant"
        assert m.merchant_type == MerchantType.BLACKSMITH
        assert m.buy_markup == 1.5
        assert m.sell_discount == 0.6

    def test_to_dict(self):
        m = MerchantDefinition(
            id="m2",
            name="M2",
            merchant_type=MerchantType.GENERAL,
            buy_markup=1.1,
        )
        data = m.to_dict()
        assert data["id"] == "m2"
        assert data["merchant_type"] == "general"
        assert data["buy_markup"] == 1.1

    def test_roundtrip(self):
        original = MerchantDefinition(
            id="m3",
            name="M3",
            merchant_type=MerchantType.ALCHEMIST,
            region_id="reg",
            location_id="loc",
            description="desc",
            metadata={"key": "val"},
        )
        restored = MerchantDefinition.from_dict(original.to_dict())
        assert restored.id == original.id
        assert restored.merchant_type == MerchantType.ALCHEMIST
        assert restored.metadata == {"key": "val"}


# ---------------------------------------------------------------------------
# PriceRule tests
# ---------------------------------------------------------------------------

class TestPriceRule(unittest.TestCase):
    def test_from_dict(self):
        data = {
            "item_id": "sword",
            "base_price": 100,
            "min_price": 10,
            "max_price": 500,
            "category_filter": "weapon",
        }
        r = PriceRule.from_dict(data)
        assert r.item_id == "sword"
        assert r.base_price == 100
        assert r.category_filter == "weapon"

    def test_roundtrip(self):
        original = PriceRule(item_id="potion", base_price=25, min_price=5, max_price=100)
        restored = PriceRule.from_dict(original.to_dict())
        assert restored.base_price == 25
        assert restored.min_price == 5


# ---------------------------------------------------------------------------
# MarketState tests
# ---------------------------------------------------------------------------

class TestMarketState(unittest.TestCase):
    def test_default_trend(self):
        state = MarketState(region_id="r1")
        assert state.get_trend("item_1") == 1.0

    def test_update_trend(self):
        state = MarketState(region_id="r1")
        state.update_trend("item_1", 0.2)
        assert state.get_trend("item_1") == 1.2

    def test_trend_clamped_min(self):
        state = MarketState(region_id="r1", volatility=0.0)
        state.item_trends = {"item_1": 0.15}
        state.update_trend("item_1", -0.2)
        assert state.get_trend("item_1") == 0.1

    def test_trend_clamped_max(self):
        state = MarketState(region_id="r1", volatility=0.0)
        state.item_trends = {"item_1": 4.9}
        state.update_trend("item_1", 0.5)
        assert state.get_trend("item_1") == 5.0

    def test_tick_random_walk(self):
        random.seed(42)
        state = MarketState(region_id="r1", item_trends={"item_1": 1.0}, volatility=0.1)
        state.tick()
        trend = state.get_trend("item_1")
        assert 0.5 < trend < 2.0

    def test_roundtrip(self):
        state = MarketState(region_id="r1", item_trends={"item_1": 1.5}, volatility=0.2)
        restored = MarketState.from_dict(state.to_dict())
        assert restored.region_id == "r1"
        assert restored.get_trend("item_1") == 1.5
        assert restored.volatility == 0.2


# ---------------------------------------------------------------------------
# Transaction tests
# ---------------------------------------------------------------------------

class TestTransaction(unittest.TestCase):
    def test_from_dict(self):
        data = {
            "transaction_id": "tx1",
            "world_id": "w1",
            "merchant_id": "m1",
            "character_id": "c1",
            "transaction_type": "buy",
            "item_id": "potion",
            "quantity": 2,
            "unit_price": 25,
            "total_price": 50,
        }
        t = Transaction.from_dict(data)
        assert t.transaction_id == "tx1"
        assert t.quantity == 2
        assert t.total_price == 50

    def test_roundtrip(self):
        original = Transaction(
            transaction_id="tx2",
            world_id="w1",
            merchant_id="m1",
            character_id="c1",
            transaction_type="sell",
            item_id="sword",
            quantity=1,
            unit_price=40,
            total_price=40,
            metadata={"reason": "test"},
        )
        restored = Transaction.from_dict(original.to_dict())
        assert restored.transaction_type == "sell"
        assert restored.metadata == {"reason": "test"}


# ---------------------------------------------------------------------------
# EconomyManager tests
# ---------------------------------------------------------------------------

class TestEconomyManager(unittest.TestCase):
    def test_register_and_get_merchant(self):
        mgr = _make_manager()
        assert mgr.get_merchant("blacksmith_01") is not None
        assert mgr.get_merchant("missing") is None

    def test_list_merchants(self):
        mgr = _make_manager()
        defs = mgr.list_merchants()
        assert len(defs) == 3
        ids = [d["id"] for d in defs]
        assert "blacksmith_01" in ids

    def test_list_merchants_by_region(self):
        mgr = _make_manager()
        defs = mgr.list_merchants(region_id="oakhaven_region")
        assert len(defs) == 2
        assert all(d["region_id"] == "oakhaven_region" for d in defs)

    def test_get_price_rule(self):
        mgr = _make_manager()
        rule = mgr.get_price_rule("blacksmith_01", "iron_sword")
        assert rule is not None
        assert rule.base_price == 50
        assert mgr.get_price_rule("blacksmith_01", "missing") is None

    # ------------------------------------------------------------------
    # Stock tests
    # ------------------------------------------------------------------

    def test_set_and_get_stock(self):
        mgr = _make_manager()
        mgr.set_stock("blacksmith_01", "iron_sword", 10)
        assert mgr.get_stock("blacksmith_01", "iron_sword") == 10
        assert mgr.get_stock("blacksmith_01", "missing") == 0

    def test_add_stock(self):
        mgr = _make_manager()
        mgr.add_stock("blacksmith_01", "iron_sword", 5)
        mgr.add_stock("blacksmith_01", "iron_sword", 3)
        assert mgr.get_stock("blacksmith_01", "iron_sword") == 8

    def test_add_stock_clamps_to_max(self):
        mgr = _make_manager()
        mgr.add_stock("blacksmith_01", "iron_sword", 200)
        assert mgr.get_stock("blacksmith_01", "iron_sword") == 99

    def test_remove_stock_success(self):
        mgr = _make_manager()
        mgr.set_stock("blacksmith_01", "iron_sword", 10)
        result = mgr.remove_stock("blacksmith_01", "iron_sword", 4)
        assert result["success"] is True
        assert mgr.get_stock("blacksmith_01", "iron_sword") == 6

    def test_remove_stock_insufficient(self):
        mgr = _make_manager()
        mgr.set_stock("blacksmith_01", "iron_sword", 3)
        result = mgr.remove_stock("blacksmith_01", "iron_sword", 5)
        assert result["success"] is False
        assert result["reason"] == "Insufficient stock."

    def test_remove_stock_missing_merchant(self):
        mgr = _make_manager()
        result = mgr.remove_stock("missing_merchant", "item", 1)
        assert result["success"] is False

    def test_get_merchant_inventory(self):
        mgr = _make_manager()
        mgr.set_stock("blacksmith_01", "iron_sword", 5)
        mgr.set_stock("blacksmith_01", "iron_ingot", 20)
        inv = mgr.get_merchant_inventory("blacksmith_01")
        item_ids = {entry["item_id"] for entry in inv}
        assert "iron_sword" in item_ids
        assert "iron_ingot" in item_ids

    # ------------------------------------------------------------------
    # Price tests
    # ------------------------------------------------------------------

    def test_get_buy_price(self):
        mgr = _make_manager()
        # blacksmith: buy_markup=1.2, iron_sword base=50, trend=1.0
        price = mgr.get_buy_price("blacksmith_01", "iron_sword", "oakhaven_region")
        assert price == int(50 * 1.2 * 1.0)  # 60

    def test_get_sell_price(self):
        mgr = _make_manager()
        # blacksmith: sell_discount=0.4, iron_sword base=50, trend=1.0
        price = mgr.get_sell_price("blacksmith_01", "iron_sword", "oakhaven_region")
        assert price == int(50 * 0.4 * 1.0)  # 20

    def test_price_with_trend(self):
        mgr = _make_manager()
        mgr.update_market_trend("oakhaven_region", "iron_sword", 0.5)
        # trend = 1.5
        price = mgr.get_buy_price("blacksmith_01", "iron_sword", "oakhaven_region")
        assert price == int(50 * 1.2 * 1.5)  # 90

    def test_price_clamped_to_min(self):
        mgr = _make_manager()
        mgr.update_market_trend("oakhaven_region", "iron_ingot", -0.9)
        # iron_ingot base=10, trend=0.1, sell_discount=0.4 => 0.4, clamped to min_price=2
        price = mgr.get_sell_price("blacksmith_01", "iron_ingot", "oakhaven_region")
        assert price >= 2

    def test_price_clamped_to_max(self):
        mgr = _make_manager()
        mgr.update_market_trend("oakhaven_region", "iron_sword", 4.0)
        # iron_sword base=50, trend=5.0, buy_markup=1.2 => 300, clamped to max_price=200
        price = mgr.get_buy_price("blacksmith_01", "iron_sword", "oakhaven_region")
        assert price <= 200

    def test_price_missing_rule_returns_zero(self):
        mgr = _make_manager()
        price = mgr.get_buy_price("blacksmith_01", "missing_item", "oakhaven_region")
        assert price == 0

    # ------------------------------------------------------------------
    # Market tests
    # ------------------------------------------------------------------

    def test_market_tick_changes_trends(self):
        random.seed(99)
        mgr = _make_manager()
        mgr.update_market_trend("oakhaven_region", "iron_sword", 0.0)
        before = mgr.get_market_trend("oakhaven_region", "iron_sword")
        mgr.tick_markets()
        after = mgr.get_market_trend("oakhaven_region", "iron_sword")
        # With seed 99 and volatility 0.1, we expect some change
        assert before != after

    def test_market_state_roundtrip(self):
        mgr = _make_manager()
        mgr.update_market_trend("oakhaven_region", "iron_sword", 0.3)
        exported = mgr.export_state()
        mgr2 = EconomyManager()
        mgr2.import_state(exported)
        assert mgr2.get_market_trend("oakhaven_region", "iron_sword") == mgr.get_market_trend("oakhaven_region", "iron_sword")

    # ------------------------------------------------------------------
    # Trade tests
    # ------------------------------------------------------------------

    def test_buy_success(self):
        mgr = _make_manager()
        mgr.set_stock("blacksmith_01", "iron_sword", 5)
        result = mgr.buy("w1", "blacksmith_01", "c1", "iron_sword", 2, "oakhaven_region")
        assert result["success"] is True
        assert result["quantity"] == 2
        assert result["remaining_stock"] == 3
        assert result["total_price"] == 120  # 60 * 2

    def test_buy_insufficient_stock(self):
        mgr = _make_manager()
        mgr.set_stock("blacksmith_01", "iron_sword", 1)
        result = mgr.buy("w1", "blacksmith_01", "c1", "iron_sword", 5, "oakhaven_region")
        assert result["success"] is False
        assert "Insufficient merchant stock" in result["reason"]

    def test_buy_missing_item_rule(self):
        mgr = _make_manager()
        mgr.set_stock("blacksmith_01", "missing_item", 5)
        result = mgr.buy("w1", "blacksmith_01", "c1", "missing_item", 1, "oakhaven_region")
        assert result["success"] is False
        assert result["reason"] == "Item not sold by this merchant."

    def test_buy_zero_quantity(self):
        mgr = _make_manager()
        result = mgr.buy("w1", "blacksmith_01", "c1", "iron_sword", 0, "oakhaven_region")
        assert result["success"] is False

    def test_sell_success(self):
        mgr = _make_manager()
        result = mgr.sell("w1", "blacksmith_01", "c1", "iron_sword", 3, "oakhaven_region")
        assert result["success"] is True
        assert result["new_stock"] == 3
        assert result["total_price"] == 60  # 20 * 3

    def test_sell_adjusts_market_down(self):
        mgr = _make_manager()
        mgr.update_market_trend("oakhaven_region", "iron_sword", 0.0)
        before = mgr.get_market_trend("oakhaven_region", "iron_sword")
        mgr.sell("w1", "blacksmith_01", "c1", "iron_sword", 10, "oakhaven_region")
        after = mgr.get_market_trend("oakhaven_region", "iron_sword")
        assert after < before

    def test_buy_adjusts_market_up(self):
        mgr = _make_manager()
        mgr.update_market_trend("oakhaven_region", "iron_sword", 0.0)
        mgr.set_stock("blacksmith_01", "iron_sword", 10)
        before = mgr.get_market_trend("oakhaven_region", "iron_sword")
        mgr.buy("w1", "blacksmith_01", "c1", "iron_sword", 10, "oakhaven_region")
        after = mgr.get_market_trend("oakhaven_region", "iron_sword")
        assert after > before

    # ------------------------------------------------------------------
    # Transaction queries
    # ------------------------------------------------------------------

    def test_list_transactions(self):
        mgr = _make_manager()
        mgr.set_stock("blacksmith_01", "iron_sword", 10)
        mgr.buy("w1", "blacksmith_01", "c1", "iron_sword", 1, "oakhaven_region")
        mgr.sell("w1", "blacksmith_01", "c1", "iron_sword", 1, "oakhaven_region")
        txs = mgr.list_transactions(world_id="w1")
        assert len(txs) == 2
        types = {t["transaction_type"] for t in txs}
        assert types == {"buy", "sell"}

    def test_list_transactions_by_character(self):
        mgr = _make_manager()
        mgr.set_stock("blacksmith_01", "iron_sword", 10)
        mgr.buy("w1", "blacksmith_01", "c1", "iron_sword", 1, "oakhaven_region")
        mgr.buy("w1", "blacksmith_01", "c2", "iron_sword", 1, "oakhaven_region")
        txs = mgr.list_transactions(character_id="c1")
        assert len(txs) == 1
        assert txs[0]["character_id"] == "c1"

    def test_get_trade_summary(self):
        mgr = _make_manager()
        mgr.set_stock("blacksmith_01", "iron_sword", 10)
        mgr.buy("w1", "blacksmith_01", "c1", "iron_sword", 2, "oakhaven_region")
        mgr.sell("w1", "blacksmith_01", "c1", "iron_sword", 1, "oakhaven_region")
        summary = mgr.get_trade_summary("w1", "c1")
        assert summary["total_transactions"] == 2
        assert summary["total_bought"] == 120
        # buy of 2 raises trend by +0.04 to 1.04; sell at 1.04 => unit_price=21
        assert summary["total_sold"] == 21
        assert summary["net_gold"] == -99

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def test_export_import_roundtrip(self):
        mgr = _make_manager()
        mgr.set_stock("blacksmith_01", "iron_sword", 7)
        mgr.update_market_trend("oakhaven_region", "iron_sword", 0.4)
        mgr.buy("w1", "blacksmith_01", "c1", "iron_sword", 2, "oakhaven_region")

        state = mgr.export_state()

        mgr2 = EconomyManager()
        mgr2.import_state(state)

        assert mgr2.get_merchant("blacksmith_01") is not None
        assert mgr2.get_stock("blacksmith_01", "iron_sword") == 5
        # buy of 2 raises trend from 1.4 by +0.04 to 1.44
        assert mgr2.get_market_trend("oakhaven_region", "iron_sword") == 1.44
        assert len(mgr2.list_transactions(world_id="w1")) == 1


if __name__ == "__main__":
    unittest.main()
