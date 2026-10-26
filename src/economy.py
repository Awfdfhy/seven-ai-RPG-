"""
RPG-10-07: Economy System
Currency, trading, merchants, and price fluctuations.

Integrates with the existing inventory gold field and world map locations.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MerchantType(Enum):
    """Broad categorization of merchant wares."""

    GENERAL = "general"
    BLACKSMITH = "blacksmith"
    ALCHEMIST = "alchemist"
    TAILOR = "tailor"
    INNKEEP = "innkeep"
    FOOD = "food"
    MAGIC = "magic"
    JEWELER = "jeweler"


class TransactionType(Enum):
    """Direction of a trade."""

    BUY = "buy"      # character buys from merchant
    SELL = "sell"    # character sells to merchant


# ---------------------------------------------------------------------------
# Definitions (static data)
# ---------------------------------------------------------------------------

@dataclass
class MerchantDefinition:
    """Static blueprint for a merchant."""

    id: str
    name: str
    merchant_type: MerchantType = MerchantType.GENERAL
    region_id: str = ""
    location_id: str = ""
    description: str = ""
    buy_markup: float = 1.0        # multiplier on base price when character buys
    sell_discount: float = 0.5     # multiplier on base price when character sells
    max_stock: int = 99
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "merchant_type": self.merchant_type.value,
            "region_id": self.region_id,
            "location_id": self.location_id,
            "description": self.description,
            "buy_markup": self.buy_markup,
            "sell_discount": self.sell_discount,
            "max_stock": self.max_stock,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> MerchantDefinition:
        return MerchantDefinition(
            id=data["id"],
            name=data["name"],
            merchant_type=MerchantType(data.get("merchant_type", "general")),
            region_id=data.get("region_id", ""),
            location_id=data.get("location_id", ""),
            description=data.get("description", ""),
            buy_markup=float(data.get("buy_markup", 1.0)),
            sell_discount=float(data.get("sell_discount", 0.5)),
            max_stock=int(data.get("max_stock", 99)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class PriceRule:
    """Defines base pricing for one item at a merchant."""

    item_id: str
    base_price: int = 10
    min_price: int = 1
    max_price: int = 10000
    category_filter: str = ""      # optional ItemCategory filter
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "base_price": self.base_price,
            "min_price": self.min_price,
            "max_price": self.max_price,
            "category_filter": self.category_filter,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> PriceRule:
        return PriceRule(
            item_id=data["item_id"],
            base_price=int(data.get("base_price", 10)),
            min_price=int(data.get("min_price", 1)),
            max_price=int(data.get("max_price", 10000)),
            category_filter=data.get("category_filter", ""),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class MerchantStock:
    """Runtime stock for a merchant: item_id -> quantity."""

    merchant_id: str
    stock: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "merchant_id": self.merchant_id,
            "stock": dict(self.stock),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> MerchantStock:
        return MerchantStock(
            merchant_id=data["merchant_id"],
            stock=dict(data.get("stock", {})),
        )


# ---------------------------------------------------------------------------
# Market state (dynamic)
# ---------------------------------------------------------------------------

@dataclass
class MarketState:
    """Tracks price trends for a region."""

    region_id: str
    item_trends: dict[str, float] = field(default_factory=dict)  # item_id -> trend multiplier
    last_updated: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    volatility: float = 0.1

    def get_trend(self, item_id: str) -> float:
        return self.item_trends.get(item_id, 1.0)

    def update_trend(self, item_id: str, delta: float) -> None:
        current = self.get_trend(item_id)
        new = max(0.1, min(5.0, current + delta))
        self.item_trends[item_id] = new
        self.last_updated = datetime.now(UTC).isoformat()

    def tick(self) -> None:
        """Random-walk every trend slightly."""
        for item_id in list(self.item_trends.keys()):
            delta = random.uniform(-self.volatility, self.volatility)
            self.update_trend(item_id, delta)
        self.last_updated = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "region_id": self.region_id,
            "item_trends": dict(self.item_trends),
            "last_updated": self.last_updated,
            "volatility": self.volatility,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> MarketState:
        return MarketState(
            region_id=data["region_id"],
            item_trends=dict(data.get("item_trends", {})),
            last_updated=data.get("last_updated", ""),
            volatility=float(data.get("volatility", 0.1)),
        )


# ---------------------------------------------------------------------------
# Transaction record
# ---------------------------------------------------------------------------

@dataclass
class Transaction:
    """One buy/sell event."""

    transaction_id: str
    world_id: str
    merchant_id: str
    character_id: str
    transaction_type: str        # "buy" or "sell"
    item_id: str
    quantity: int
    unit_price: int
    total_price: int
    occurred_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "world_id": self.world_id,
            "merchant_id": self.merchant_id,
            "character_id": self.character_id,
            "transaction_type": self.transaction_type,
            "item_id": self.item_id,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total_price": self.total_price,
            "occurred_at": self.occurred_at,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Transaction:
        return Transaction(
            transaction_id=data["transaction_id"],
            world_id=data["world_id"],
            merchant_id=data["merchant_id"],
            character_id=data["character_id"],
            transaction_type=data["transaction_type"],
            item_id=data["item_id"],
            quantity=int(data["quantity"]),
            unit_price=int(data["unit_price"]),
            total_price=int(data["total_price"]),
            occurred_at=data.get("occurred_at", ""),
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class EconomyManager:
    """
    Manages merchant definitions, runtime stock, market trends,
    and transaction history scoped to worlds and characters.
    """

    def __init__(self) -> None:
        self._definitions: dict[str, MerchantDefinition] = {}
        self._price_rules: dict[str, dict[str, PriceRule]] = {}  # merchant_id -> item_id -> rule
        self._merchant_stock: dict[str, MerchantStock] = {}      # merchant_id -> stock
        self._market_states: dict[str, MarketState] = {}         # region_id -> state
        self._transactions: dict[str, Transaction] = {}          # transaction_id -> record
        self._world_transactions: dict[str, set[str]] = {}       # world_id -> transaction_ids
        self._character_transactions: dict[str, set[str]] = {}   # character_id -> transaction_ids
        self._inventory_manager: Any = None

    # ------------------------------------------------------------------
    # Definition loading
    # ------------------------------------------------------------------

    def register_merchant(self, merchant: MerchantDefinition) -> None:
        self._definitions[merchant.id] = merchant

    def load_merchants(self, merchants: list[MerchantDefinition]) -> None:
        for m in merchants:
            self.register_merchant(m)

    def add_price_rule(self, merchant_id: str, rule: PriceRule) -> None:
        self._price_rules.setdefault(merchant_id, {})[rule.item_id] = rule

    def load_price_rules(self, merchant_id: str, rules: list[PriceRule]) -> None:
        for r in rules:
            self.add_price_rule(merchant_id, r)

    def get_merchant(self, merchant_id: str) -> MerchantDefinition | None:
        return self._definitions.get(merchant_id)

    def list_merchants(self, region_id: str | None = None) -> list[dict[str, Any]]:
        merchants = list(self._definitions.values())
        if region_id is not None:
            merchants = [m for m in merchants if m.region_id == region_id]
        return [m.to_dict() for m in sorted(merchants, key=lambda m: m.name.lower())]

    def get_price_rule(self, merchant_id: str, item_id: str) -> PriceRule | None:
        return self._price_rules.get(merchant_id, {}).get(item_id)

    def set_inventory_manager(self, inventory_manager: Any) -> None:
        """Attach an InventoryManager so gold can be updated on trade."""
        self._inventory_manager = inventory_manager

    # ------------------------------------------------------------------
    # Gold helpers
    # ------------------------------------------------------------------

    def _get_character_gold(self, character_id: str) -> int:
        if self._inventory_manager is None:
            return 0
        inv = self._inventory_manager.get_inventory(character_id)
        return inv.gold

    def _set_character_gold(self, character_id: str, amount: int) -> None:
        if self._inventory_manager is None:
            return
        inv = self._inventory_manager.get_inventory(character_id)
        inv.gold = max(0, amount)

    # ------------------------------------------------------------------
    # Stock management
    # ------------------------------------------------------------------

    def ensure_merchant_stock(self, merchant_id: str) -> MerchantStock:
        if merchant_id not in self._merchant_stock:
            self._merchant_stock[merchant_id] = MerchantStock(merchant_id=merchant_id)
        return self._merchant_stock[merchant_id]

    def set_stock(self, merchant_id: str, item_id: str, quantity: int) -> None:
        stock = self.ensure_merchant_stock(merchant_id)
        stock.stock[item_id] = max(0, quantity)

    def get_stock(self, merchant_id: str, item_id: str) -> int:
        stock = self._merchant_stock.get(merchant_id)
        if stock is None:
            return 0
        return stock.stock.get(item_id, 0)

    def add_stock(self, merchant_id: str, item_id: str, quantity: int) -> None:
        stock = self.ensure_merchant_stock(merchant_id)
        current = stock.stock.get(item_id, 0)
        merchant = self._definitions.get(merchant_id)
        max_stock = merchant.max_stock if merchant else 99
        stock.stock[item_id] = min(max_stock, current + quantity)

    def remove_stock(self, merchant_id: str, item_id: str, quantity: int) -> dict[str, Any]:
        stock = self._merchant_stock.get(merchant_id)
        if stock is None:
            return {"success": False, "reason": "Merchant not initialized."}
        current = stock.stock.get(item_id, 0)
        if current < quantity:
            return {
                "success": False,
                "reason": "Insufficient stock.",
                "available": current,
                "requested": quantity,
            }
        stock.stock[item_id] = current - quantity
        return {"success": True, "remaining": stock.stock[item_id]}

    def get_merchant_inventory(self, merchant_id: str) -> list[dict[str, Any]]:
        stock = self._merchant_stock.get(merchant_id)
        if stock is None:
            return []
        rules = self._price_rules.get(merchant_id, {})
        result = []
        for item_id, qty in sorted(stock.stock.items()):
            rule = rules.get(item_id)
            result.append({
                "item_id": item_id,
                "quantity": qty,
                "base_price": rule.base_price if rule else 0,
                "min_price": rule.min_price if rule else 0,
                "max_price": rule.max_price if rule else 0,
            })
        return result

    # ------------------------------------------------------------------
    # Market state
    # ------------------------------------------------------------------

    def get_or_create_market_state(self, region_id: str) -> MarketState:
        if region_id not in self._market_states:
            self._market_states[region_id] = MarketState(region_id=region_id)
        return self._market_states[region_id]

    def update_market_trend(self, region_id: str, item_id: str, delta: float) -> None:
        state = self.get_or_create_market_state(region_id)
        state.update_trend(item_id, delta)

    def tick_markets(self) -> list[dict[str, Any]]:
        """Advance all market states by one tick."""
        results = []
        for region_id, state in self._market_states.items():
            state.tick()
            results.append(state.to_dict())
        return results

    def get_market_trend(self, region_id: str, item_id: str) -> float:
        state = self._market_states.get(region_id)
        if state is None:
            return 1.0
        return state.get_trend(item_id)

    # ------------------------------------------------------------------
    # Price calculation
    # ------------------------------------------------------------------

    def calculate_price(
        self,
        merchant_id: str,
        item_id: str,
        transaction_type: TransactionType,
        region_id: str = "",
    ) -> int:
        """
        Return the effective price for one unit of `item_id` at `merchant_id`
        for the given transaction direction.
        """
        merchant = self._definitions.get(merchant_id)
        if merchant is None:
            return 0

        rule = self._price_rules.get(merchant_id, {}).get(item_id)
        if rule is None:
            return 0

        base = rule.base_price
        trend = self.get_market_trend(region_id or merchant.region_id, item_id)

        if transaction_type == TransactionType.BUY:
            price = base * merchant.buy_markup * trend
        else:
            price = base * merchant.sell_discount * trend

        return max(rule.min_price, min(rule.max_price, int(round(price))))

    def get_buy_price(self, merchant_id: str, item_id: str, region_id: str = "") -> int:
        """Price the merchant charges the character to buy an item."""
        return self.calculate_price(merchant_id, item_id, TransactionType.BUY, region_id)

    def get_sell_price(self, merchant_id: str, item_id: str, region_id: str = "") -> int:
        """Price the merchant pays the character for selling an item."""
        return self.calculate_price(merchant_id, item_id, TransactionType.SELL, region_id)

    # ------------------------------------------------------------------
    # Trading
    # ------------------------------------------------------------------

    def buy(
        self,
        world_id: str,
        merchant_id: str,
        character_id: str,
        item_id: str,
        quantity: int = 1,
        region_id: str = "",
    ) -> dict[str, Any]:
        """
        Character buys `quantity` of `item_id` from `merchant_id`.
        Returns success/failure with updated stock and transaction record.
        """
        if quantity < 1:
            return {"success": False, "reason": "Quantity must be >= 1."}

        merchant = self._definitions.get(merchant_id)
        if merchant is None:
            return {"success": False, "reason": "Merchant not found."}

        stock = self._merchant_stock.get(merchant_id)
        if stock is None:
            return {"success": False, "reason": "Merchant has no stock."}

        available = stock.stock.get(item_id, 0)
        if available < quantity:
            return {
                "success": False,
                "reason": "Insufficient merchant stock.",
                "available": available,
                "requested": quantity,
            }

        unit_price = self.get_buy_price(merchant_id, item_id, region_id or merchant.region_id)
        if unit_price <= 0:
            return {"success": False, "reason": "Item not sold by this merchant."}

        total = unit_price * quantity

        if self._inventory_manager is not None and self._get_character_gold(character_id) < total:
            return {
                "success": False,
                "reason": "Insufficient gold.",
                "required": total,
                "available": self._get_character_gold(character_id),
            }

        tx = Transaction(
            transaction_id=str(uuid.uuid4()),
            world_id=world_id,
            merchant_id=merchant_id,
            character_id=character_id,
            transaction_type=TransactionType.BUY.value,
            item_id=item_id,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total,
        )

        # Update stock
        stock.stock[item_id] = available - quantity
        if stock.stock[item_id] <= 0:
            del stock.stock[item_id]

        # Deduct gold if inventory manager is attached
        if self._inventory_manager is not None:
            self._set_character_gold(character_id, self._get_character_gold(character_id) - total)

        # Record transaction
        self._transactions[tx.transaction_id] = tx
        self._world_transactions.setdefault(world_id, set()).add(tx.transaction_id)
        self._character_transactions.setdefault(character_id, set()).add(tx.transaction_id)

        # Adjust market trend: buying increases local demand slightly
        self.update_market_trend(region_id or merchant.region_id, item_id, 0.02 * quantity)

        return {
            "success": True,
            "transaction_id": tx.transaction_id,
            "item_id": item_id,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": total,
            "remaining_stock": stock.stock.get(item_id, 0),
        }

    def sell(
        self,
        world_id: str,
        merchant_id: str,
        character_id: str,
        item_id: str,
        quantity: int = 1,
        region_id: str = "",
    ) -> dict[str, Any]:
        """
        Character sells `quantity` of `item_id` to `merchant_id`.
        Returns success/failure with updated stock and transaction record.
        """
        if quantity < 1:
            return {"success": False, "reason": "Quantity must be >= 1."}

        merchant = self._definitions.get(merchant_id)
        if merchant is None:
            return {"success": False, "reason": "Merchant not found."}

        unit_price = self.get_sell_price(merchant_id, item_id, region_id or merchant.region_id)
        if unit_price <= 0:
            return {"success": False, "reason": "Merchant does not buy this item."}

        stock = self.ensure_merchant_stock(merchant_id)
        current = stock.stock.get(item_id, 0)
        max_stock = merchant.max_stock
        new_qty = min(max_stock, current + quantity)
        stock.stock[item_id] = new_qty

        total = unit_price * quantity

        # Add gold if inventory manager is attached
        if self._inventory_manager is not None:
            self._set_character_gold(character_id, self._get_character_gold(character_id) + total)

        tx = Transaction(
            transaction_id=str(uuid.uuid4()),
            world_id=world_id,
            merchant_id=merchant_id,
            character_id=character_id,
            transaction_type=TransactionType.SELL.value,
            item_id=item_id,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total,
        )

        self._transactions[tx.transaction_id] = tx
        self._world_transactions.setdefault(world_id, set()).add(tx.transaction_id)
        self._character_transactions.setdefault(character_id, set()).add(tx.transaction_id)

        # Selling increases supply, lowering trend slightly
        self.update_market_trend(region_id or merchant.region_id, item_id, -0.01 * quantity)

        return {
            "success": True,
            "transaction_id": tx.transaction_id,
            "item_id": item_id,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": total,
            "new_stock": stock.stock.get(item_id, 0),
        }

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_transaction(self, transaction_id: str) -> Transaction | None:
        return self._transactions.get(transaction_id)

    def list_transactions(
        self,
        world_id: str | None = None,
        character_id: str | None = None,
        merchant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        txs = list(self._transactions.values())
        if world_id is not None:
            txs = [t for t in txs if t.world_id == world_id]
        if character_id is not None:
            txs = [t for t in txs if t.character_id == character_id]
        if merchant_id is not None:
            txs = [t for t in txs if t.merchant_id == merchant_id]
        return [t.to_dict() for t in sorted(txs, key=lambda t: t.occurred_at)]

    def get_trade_summary(self, world_id: str, character_id: str) -> dict[str, Any]:
        txs = [t for t in self._transactions.values()
               if t.world_id == world_id and t.character_id == character_id]
        total_bought = sum(t.total_price for t in txs if t.transaction_type == TransactionType.BUY.value)
        total_sold = sum(t.total_price for t in txs if t.transaction_type == TransactionType.SELL.value)
        net_gold = total_sold - total_bought
        return {
            "world_id": world_id,
            "character_id": character_id,
            "total_transactions": len(txs),
            "total_bought": total_bought,
            "total_sold": total_sold,
            "net_gold": net_gold,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def export_state(self) -> dict[str, Any]:
        return {
            "definitions": {k: v.to_dict() for k, v in self._definitions.items()},
            "price_rules": {
                mid: {iid: r.to_dict() for iid, r in rules.items()}
                for mid, rules in self._price_rules.items()
            },
            "merchant_stock": {k: v.to_dict() for k, v in self._merchant_stock.items()},
            "market_states": {k: v.to_dict() for k, v in self._market_states.items()},
            "transactions": {k: v.to_dict() for k, v in self._transactions.items()},
        }

    def import_state(self, state: dict[str, Any]) -> None:
        self._definitions.clear()
        self._price_rules.clear()
        self._merchant_stock.clear()
        self._market_states.clear()
        self._transactions.clear()
        self._world_transactions.clear()
        self._character_transactions.clear()

        for mid, mdata in state.get("definitions", {}).items():
            self._definitions[mid] = MerchantDefinition.from_dict(mdata)

        for mid, rules in state.get("price_rules", {}).items():
            self._price_rules[mid] = {iid: PriceRule.from_dict(r) for iid, r in rules.items()}

        for mid, sdata in state.get("merchant_stock", {}).items():
            self._merchant_stock[mid] = MerchantStock.from_dict(sdata)

        for rid, mdata in state.get("market_states", {}).items():
            self._market_states[rid] = MarketState.from_dict(mdata)

        for tid, tdata in state.get("transactions", {}).items():
            tx = Transaction.from_dict(tdata)
            self._transactions[tid] = tx
            self._world_transactions.setdefault(tx.world_id, set()).add(tid)
            self._character_transactions.setdefault(tx.character_id, set()).add(tid)
