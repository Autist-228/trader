import pandas as pd
import numpy as np
import ta


def build_features(candles: list[dict], ticker: dict = None, oi_data: list[dict] = None) -> pd.DataFrame:
    df = pd.DataFrame(candles)
    if len(df) < 50:
        return pd.DataFrame()

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]
    op = df["open"]

    df["rsi_14"] = ta.momentum.RSIIndicator(close, window=14).rsi()
    df["rsi_7"] = ta.momentum.RSIIndicator(close, window=7).rsi()
    df["rsi_21"] = ta.momentum.RSIIndicator(close, window=21).rsi()

    macd = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"] = macd.macd_diff()

    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()
    df["bb_mid"] = bb.bollinger_mavg()
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]
    df["bb_pct"] = (close - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])

    for period in [7, 14, 21, 50, 100]:
        df[f"ema_{period}"] = ta.trend.EMAIndicator(close, window=period).ema_indicator()
    for period in [20, 50]:
        df[f"sma_{period}"] = ta.trend.SMAIndicator(close, window=period).sma_indicator()

    df["ema_cross_7_21"] = (df["ema_7"] - df["ema_21"]) / close
    df["ema_cross_14_50"] = (df["ema_14"] - df["ema_50"]) / close
    df["price_vs_ema_50"] = (close - df["ema_50"]) / close
    df["price_vs_sma_20"] = (close - df["sma_20"]) / close

    df["atr_14"] = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range()
    df["atr_7"] = ta.volatility.AverageTrueRange(high, low, close, window=7).average_true_range()
    df["atr_pct"] = df["atr_14"] / close

    stoch = ta.momentum.StochasticOscillator(high, low, close, window=14, smooth_window=3)
    df["stoch_k"] = stoch.stoch()
    df["stoch_d"] = stoch.stoch_signal()

    df["adx"] = ta.trend.ADXIndicator(high, low, close, window=14).adx()
    df["di_plus"] = ta.trend.ADXIndicator(high, low, close, window=14).adx_pos()
    df["di_minus"] = ta.trend.ADXIndicator(high, low, close, window=14).adx_neg()

    df["obv"] = ta.volume.OnBalanceVolumeIndicator(close, volume).on_balance_volume()
    df["obv_change"] = df["obv"].pct_change(5)

    df["vwap"] = (volume * (high + low + close) / 3).cumsum() / volume.cumsum()
    df["price_vs_vwap"] = (close - df["vwap"]) / close

    df["mfi"] = ta.volume.MFIIndicator(high, low, close, volume, window=14).money_flow_index()

    df["cci"] = ta.trend.CCIIndicator(high, low, close, window=20).cci()

    williams = ta.momentum.WilliamsRIndicator(high, low, close, lbp=14)
    df["williams_r"] = williams.williams_r()

    df["vol_change_5"] = volume.pct_change(5)
    df["vol_change_10"] = volume.pct_change(10)
    df["vol_sma_20"] = volume.rolling(20).mean()
    df["vol_ratio"] = volume / df["vol_sma_20"]

    for period in [1, 3, 5, 10, 20]:
        df[f"return_{period}"] = close.pct_change(period)

    df["high_low_range"] = (high - low) / close
    df["close_open_range"] = (close - op) / close
    df["upper_shadow"] = (high - np.maximum(close, op)) / close
    df["lower_shadow"] = (np.minimum(close, op) - low) / close

    df["volatility_5"] = close.pct_change().rolling(5).std()
    df["volatility_20"] = close.pct_change().rolling(20).std()
    df["vol_ratio_5_20"] = df["volatility_5"] / df["volatility_20"]

    df["highest_20"] = high.rolling(20).max()
    df["lowest_20"] = low.rolling(20).min()
    df["price_position"] = (close - df["lowest_20"]) / (df["highest_20"] - df["lowest_20"])

    if ticker:
        df["funding_rate"] = ticker.get("funding_rate", 0)
        df["open_interest_val"] = ticker.get("open_interest", 0)
        df["price_change_24h"] = ticker.get("price_change_24h", 0)
        df["volume_24h"] = ticker.get("volume_24h", 0)
    else:
        df["funding_rate"] = 0
        df["open_interest_val"] = 0
        df["price_change_24h"] = 0
        df["volume_24h"] = 0

    if oi_data and len(oi_data) > 1:
        oi_values = [x["open_interest"] for x in oi_data]
        oi_change = (oi_values[-1] - oi_values[0]) / oi_values[0] if oi_values[0] != 0 else 0
        df["oi_change"] = oi_change
    else:
        df["oi_change"] = 0

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.fillna(method="ffill").fillna(0)

    return df


FEATURE_COLUMNS = [
    "rsi_14", "rsi_7", "rsi_21",
    "macd", "macd_signal", "macd_hist",
    "bb_width", "bb_pct",
    "ema_cross_7_21", "ema_cross_14_50", "price_vs_ema_50", "price_vs_sma_20",
    "atr_14", "atr_7", "atr_pct",
    "stoch_k", "stoch_d",
    "adx", "di_plus", "di_minus",
    "obv_change",
    "price_vs_vwap",
    "mfi", "cci", "williams_r",
    "vol_change_5", "vol_change_10", "vol_ratio",
    "return_1", "return_3", "return_5", "return_10", "return_20",
    "high_low_range", "close_open_range", "upper_shadow", "lower_shadow",
    "volatility_5", "volatility_20", "vol_ratio_5_20",
    "price_position",
    "funding_rate", "open_interest_val", "price_change_24h",
    "oi_change",
]
