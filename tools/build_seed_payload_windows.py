"""Build an encrypted broker-seeded OHLC payload from VASTcode21 local v0.6.

This Windows-only helper deliberately depends only on modules that exist in local v0.6.
It fetches broker OHLC data through MetaTrader 5, writes the cloud seed format locally,
packages it, and encrypts the package with the local VASTcode21 key.
No broker password/login token is exported.
"""
from __future__ import annotations

import argparse
import json
import sys
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from crypto_utils import encrypt_file


def write_seed_dataset(asset, timeframe, broker_symbol, spread_price, df, root):
    """Write the same broker-seed format consumed by the encrypted cloud core."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    stem = f"{asset.upper()}_{timeframe.upper()}"
    csv_path = root / f"{stem}.csv.gz"
    meta_path = root / f"{stem}.json"

    cols = [
        c
        for c in ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
        if c in df.columns
    ]
    out = df[cols].copy()
    # pandas is already a dependency of the local VASTcode21 environment.
    import pandas as pd

    out["time"] = pd.to_datetime(out["time"], utc=True)
    out.to_csv(csv_path, index=False, compression="gzip")
    meta = {
        "asset": asset.upper(),
        "timeframe": timeframe.upper(),
        "broker_symbol": broker_symbol,
        "spread_price": float(spread_price),
        "rows": int(len(out)),
        "first_time": out["time"].iloc[0].isoformat() if len(out) else None,
        "last_time": out["time"].iloc[-1].isoformat() if len(out) else None,
        "purpose": "broker-specific cloud research seed; not tick-execution validation",
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return csv_path, meta_path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", default=str(Path.home() / "VASTcode21" / "VASTcode21_local_v0.6"))
    p.add_argument("--bars", type=int, default=30000)
    p.add_argument("--out", default=str(HERE.parent / "payload" / "seed.enc"))
    p.add_argument("--key-file", default=str(HERE.parent / "LOCAL_ONLY" / "VC21_CORE_KEY.txt"))
    a = p.parse_args()

    source = Path(a.source)
    if not source.exists():
        raise SystemExit(f"Local VASTcode21 source not found: {source}")
    sys.path.insert(0, str(source))
    try:
        from vastcode21.trading.mt5_data import fetch_asset_rates
    except Exception as e:
        raise SystemExit(f"Could not import VASTcode21 local MT5 module from {source}: {e}")

    key_file = Path(a.key_file)
    if not key_file.exists():
        raise SystemExit(f"Local encryption key file not found: {key_file}")
    key = key_file.read_text(encoding="utf-8").strip()

    with tempfile.TemporaryDirectory(prefix="vc21_seed_") as td:
        tdp = Path(td)
        seedroot = tdp / "data" / "cloud_seed"
        for asset in ("GOLD", "BITCOIN"):
            for tf in ("M15", "H1"):
                symbol, df, spread = fetch_asset_rates(asset, tf, a.bars, 60)
                csv_path, meta_path = write_seed_dataset(asset, tf, symbol, spread, df, seedroot)
                print(f"{asset} {tf}: {symbol}, {len(df)} rows -> {csv_path.name}")
        tarpath = tdp / "seed.tar.gz"
        with tarfile.open(tarpath, "w:gz") as tf:
            tf.add(seedroot, arcname="data/cloud_seed")
        encrypt_file(tarpath, Path(a.out), key)

    print(f"Encrypted seed payload ready: {a.out}")


if __name__ == "__main__":
    main()
