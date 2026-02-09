PRESETS = {
    "conservative": {
        "name": "Conservative",
        "emoji": "\ud83d\udfe2",
        "description": "Low risk, high confidence trades only",
        "leverage_min": 1.0,
        "leverage_max": 3.0,
        "position_size_min": 1.0,
        "position_size_max": 2.0,
        "sl_min": 1.0,
        "sl_max": 2.0,
        "tp_min": 2.0,
        "tp_max": 4.0,
        "max_daily_loss": 3.0,
        "max_drawdown": 10.0,
        "max_positions": 2,
        "min_confidence": 75.0,
        "coins": ["BTCUSDT", "ETHUSDT"],
        "timeframes": ["60", "240"],
    },
    "balanced": {
        "name": "Balanced",
        "emoji": "\ud83d\udfe1",
        "description": "Medium risk, balanced approach",
        "leverage_min": 2.0,
        "leverage_max": 5.0,
        "position_size_min": 2.0,
        "position_size_max": 5.0,
        "sl_min": 1.5,
        "sl_max": 3.0,
        "tp_min": 3.0,
        "tp_max": 6.0,
        "max_daily_loss": 5.0,
        "max_drawdown": 15.0,
        "max_positions": 3,
        "min_confidence": 65.0,
        "coins": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "BNBUSDT"],
        "timeframes": ["15", "60", "240"],
    },
    "aggressive": {
        "name": "Aggressive",
        "emoji": "\ud83d\udd34",
        "description": "High risk, high reward",
        "leverage_min": 3.0,
        "leverage_max": 10.0,
        "position_size_min": 3.0,
        "position_size_max": 10.0,
        "sl_min": 2.0,
        "sl_max": 5.0,
        "tp_min": 4.0,
        "tp_max": 10.0,
        "max_daily_loss": 10.0,
        "max_drawdown": 25.0,
        "max_positions": 5,
        "min_confidence": 55.0,
        "coins": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "BNBUSDT"],
        "timeframes": ["5", "15", "60"],
    },
    "bankroll_boost": {
        "name": "Bankroll Boost",
        "emoji": "\U0001f680",
        "description": "Aggressive bankroll boost: $10 -> $50 slots",
        "leverage_min": 15.0,
        "leverage_max": 20.0,
        "position_size_min": 80.0,
        "position_size_max": 95.0,
        "sl_min": 2.0,
        "sl_max": 3.5,
        "tp_min": 2.0,
        "tp_max": 4.0,
        "max_daily_loss": 80.0,
        "max_drawdown": 90.0,
        "max_positions": 1,
        "min_confidence": 62.0,
        "coins": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "BNBUSDT"],
        "timeframes": ["5", "15"],
    },
}


def get_preset(name: str) -> dict:
    return PRESETS.get(name, PRESETS["balanced"])


def apply_preset(preset_name: str) -> dict:
    preset = get_preset(preset_name)
    return {
        "leverage_min": preset["leverage_min"],
        "leverage_max": preset["leverage_max"],
        "position_size_min": preset["position_size_min"],
        "position_size_max": preset["position_size_max"],
        "sl_min": preset["sl_min"],
        "sl_max": preset["sl_max"],
        "tp_min": preset["tp_min"],
        "tp_max": preset["tp_max"],
        "max_daily_loss": preset["max_daily_loss"],
        "max_drawdown": preset["max_drawdown"],
        "max_positions": preset["max_positions"],
        "min_confidence": preset["min_confidence"],
        "coins": preset["coins"],
    }


def calculate_adaptive_params(preset_name: str, confidence: float, atr_pct: float) -> dict:
    preset = get_preset(preset_name)
    conf_norm = max(0, min(1, (confidence - preset["min_confidence"]) / (100 - preset["min_confidence"])))

    leverage = preset["leverage_min"] + conf_norm * (preset["leverage_max"] - preset["leverage_min"])
    leverage = round(leverage)

    pos_size = preset["position_size_min"] + conf_norm * (preset["position_size_max"] - preset["position_size_min"])

    base_sl = preset["sl_min"] + (1 - conf_norm) * (preset["sl_max"] - preset["sl_min"])
    sl_pct = max(base_sl, atr_pct * 100 * 1.5)
    sl_pct = min(sl_pct, preset["sl_max"])

    base_tp = preset["tp_min"] + conf_norm * (preset["tp_max"] - preset["tp_min"])
    tp1_pct = base_tp * 0.5
    tp2_pct = base_tp * 0.75
    tp3_pct = base_tp

    return {
        "leverage": max(1, int(leverage)),
        "position_size_pct": round(pos_size, 2),
        "sl_pct": round(sl_pct, 2),
        "tp1_pct": round(tp1_pct, 2),
        "tp2_pct": round(tp2_pct, 2),
        "tp3_pct": round(tp3_pct, 2),
    }
