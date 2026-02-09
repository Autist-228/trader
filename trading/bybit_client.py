import logging
from pybit.unified_trading import HTTP
from config import CATEGORY, SUPPORTED_COINS

logger = logging.getLogger(__name__)


class BybitClient:
    def __init__(self, api_key: str, api_secret: str):
        self.session = HTTP(api_key=api_key, api_secret=api_secret)

    def get_balance(self) -> dict:
        try:
            result = self.session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
            coins = result["result"]["list"][0]["coin"]
            for c in coins:
                if c["coin"] == "USDT":
                    return {
                        "total": float(c["walletBalance"]),
                        "available": float(c["availableToWithdraw"]),
                        "unrealized_pnl": float(c["unrealisedPnl"]),
                    }
            return {"total": 0.0, "available": 0.0, "unrealized_pnl": 0.0}
        except Exception as e:
            logger.error(f"Balance error: {e}")
            return None

    def get_klines(self, symbol: str, interval: str = "15", limit: int = 200) -> list[dict]:
        try:
            result = self.session.get_kline(
                category=CATEGORY, symbol=symbol, interval=interval, limit=limit
            )
            rows = result["result"]["list"]
            candles = []
            for r in rows:
                candles.append({
                    "timestamp": int(r[0]),
                    "open": float(r[1]),
                    "high": float(r[2]),
                    "low": float(r[3]),
                    "close": float(r[4]),
                    "volume": float(r[5]),
                    "turnover": float(r[6]),
                })
            candles.reverse()
            return candles
        except Exception as e:
            logger.error(f"Klines error for {symbol}: {e}")
            return []

    def get_ticker(self, symbol: str) -> dict | None:
        try:
            result = self.session.get_tickers(category=CATEGORY, symbol=symbol)
            t = result["result"]["list"][0]
            return {
                "symbol": t["symbol"],
                "last_price": float(t["lastPrice"]),
                "bid": float(t["bid1Price"]) if t["bid1Price"] else 0,
                "ask": float(t["ask1Price"]) if t["ask1Price"] else 0,
                "volume_24h": float(t["volume24h"]),
                "turnover_24h": float(t["turnover24h"]),
                "price_change_24h": float(t["price24hPcnt"]),
                "funding_rate": float(t["fundingRate"]) if t.get("fundingRate") else 0,
                "open_interest": float(t["openInterest"]) if t.get("openInterest") else 0,
            }
        except Exception as e:
            logger.error(f"Ticker error for {symbol}: {e}")
            return None

    def get_open_interest(self, symbol: str, interval: str = "15min", limit: int = 50) -> list[dict]:
        try:
            result = self.session.get_open_interest(
                category=CATEGORY, symbol=symbol,
                intervalTime=interval, limit=limit
            )
            rows = result["result"]["list"]
            data = []
            for r in rows:
                data.append({
                    "timestamp": int(r["timestamp"]),
                    "open_interest": float(r["openInterest"]),
                })
            data.reverse()
            return data
        except Exception as e:
            logger.error(f"OI error for {symbol}: {e}")
            return []

    def get_instrument_info(self, symbol: str) -> dict | None:
        try:
            result = self.session.get_instruments_info(category=CATEGORY, symbol=symbol)
            info = result["result"]["list"][0]
            lot = info["lotSizeFilter"]
            price_f = info["priceFilter"]
            return {
                "min_qty": float(lot["minOrderQty"]),
                "max_qty": float(lot["maxOrderQty"]),
                "qty_step": float(lot["qtyStep"]),
                "min_price": float(price_f["minPrice"]),
                "max_price": float(price_f["maxPrice"]),
                "tick_size": float(price_f["tickSize"]),
                "max_leverage": float(info["leverageFilter"]["maxLeverage"]),
            }
        except Exception as e:
            logger.error(f"Instrument info error for {symbol}: {e}")
            return None

    def set_leverage(self, symbol: str, leverage: int) -> bool:
        try:
            self.session.set_leverage(
                category=CATEGORY, symbol=symbol,
                buyLeverage=str(leverage), sellLeverage=str(leverage)
            )
            return True
        except Exception as e:
            if "leverage not modified" in str(e).lower() or "110043" in str(e):
                return True
            logger.error(f"Set leverage error for {symbol}: {e}")
            return False

    def place_order(
        self, symbol: str, side: str, qty: float, order_type: str = "Market",
        price: float = None, sl_price: float = None, tp_price: float = None,
    ) -> dict | None:
        try:
            params = {
                "category": CATEGORY,
                "symbol": symbol,
                "side": side,
                "orderType": order_type,
                "qty": str(qty),
            }
            if price and order_type == "Limit":
                params["price"] = str(price)
            if sl_price:
                params["stopLoss"] = str(sl_price)
            if tp_price:
                params["takeProfit"] = str(tp_price)
            result = self.session.place_order(**params)
            return {
                "order_id": result["result"]["orderId"],
                "order_link_id": result["result"].get("orderLinkId", ""),
            }
        except Exception as e:
            logger.error(f"Place order error: {e}")
            return None

    def close_position(self, symbol: str, side: str, qty: float) -> dict | None:
        close_side = "Sell" if side == "Buy" else "Buy"
        return self.place_order(symbol=symbol, side=close_side, qty=qty)

    def get_positions(self, symbol: str = None) -> list[dict]:
        try:
            params = {"category": CATEGORY}
            if symbol:
                params["symbol"] = symbol
            result = self.session.get_positions(**params)
            positions = []
            for p in result["result"]["list"]:
                size = float(p["size"])
                if size > 0:
                    positions.append({
                        "symbol": p["symbol"],
                        "side": p["side"],
                        "size": size,
                        "entry_price": float(p["avgPrice"]),
                        "mark_price": float(p["markPrice"]),
                        "unrealized_pnl": float(p["unrealisedPnl"]),
                        "leverage": float(p["leverage"]),
                        "liq_price": float(p["liqPrice"]) if p["liqPrice"] else 0,
                    })
            return positions
        except Exception as e:
            logger.error(f"Get positions error: {e}")
            return []

    def cancel_all_orders(self, symbol: str) -> bool:
        try:
            self.session.cancel_all_orders(category=CATEGORY, symbol=symbol)
            return True
        except Exception as e:
            logger.error(f"Cancel orders error: {e}")
            return False

    def validate_keys(self) -> bool:
        try:
            self.get_balance()
            return True
        except Exception:
            return False
