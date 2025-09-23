#!/usr/bin/env python3
"""
save_iface_stats.py
Stáhne rozhraní z REST endpointu, najde MAC D4:CA:6D:9E:F8:A0 a uloží rx/tx bytes.
Podporuje HTTP Basic Auth (uživatel + heslo) a self-signed certifikát.
"""

import argparse
import requests
import os
import csv
import sqlite3
import urllib3
from datetime import datetime
from requests.auth import HTTPBasicAuth
from typing import Any, Dict, Optional

TARGET_MAC = "D4:CA:6D:9E:F8:A0"

RX_KEYS = {"rx_bytes", "rxBytes", "rx", "rx_octets", "rx_octet", "rx_octet_count", "rx_bytes_total"}
TX_KEYS = {"tx_bytes", "txBytes", "tx", "tx_octets", "tx_octet", "tx_octet_count", "tx_bytes_total"}

def norm_mac(mac: str) -> str:
    s = mac.strip().upper().replace("-", ":").replace(".", "").replace(" ", "")
    if ":" not in s and len(s) == 12:
        s = ":".join(s[i:i+2] for i in range(0, 12, 2))
    return s

def find_in_dict(obj: Any, keyset: set):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keyset:
                return v
            found = find_in_dict(v, keyset)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_in_dict(item, keyset)
            if found is not None:
                return found
    return None

def find_mac_record(json_obj: Any, target_mac: str) -> Optional[Dict]:
    mac_keys = {"mac", "mac_address", "macAddress", "hwaddr", "hardware_address", "address"}
    target = norm_mac(target_mac)
    def recurse(obj):
        if isinstance(obj, dict):
            for mk in mac_keys:
                if mk in obj:
                    try:
                        if norm_mac(str(obj[mk])) == target:
                            return obj
                    except Exception:
                        pass
            for v in obj.values():
                res = recurse(v)
                if res:
                    return res
        elif isinstance(obj, list):
            for item in obj:
                res = recurse(item)
                if res:
                    return res
        return None
    return recurse(json_obj)

def extract_rx_tx(record: Dict) -> (Optional[int], Optional[int]):
    rx_val = find_in_dict(record, RX_KEYS)
    tx_val = find_in_dict(record, TX_KEYS)
    try:
        rx = int(rx_val) if rx_val is not None else None
    except Exception:
        rx = None
    try:
        tx = int(tx_val) if tx_val is not None else None
    except Exception:
        tx = None
    return rx, tx

def save_to_csv(path: str, row: Dict):
    header = ["timestamp", "mac", "rx_bytes", "tx_bytes"]
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if not exists:
            w.writeheader()
        w.writerow(row)

def save_to_sqlite(db_path: str, row: Dict):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS iface_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            mac TEXT,
            rx_bytes INTEGER,
            tx_bytes INTEGER
        )
    """)
    cur.execute("INSERT INTO iface_stats (timestamp, mac, rx_bytes, tx_bytes) VALUES (?, ?, ?, ?)",
                (row["timestamp"], row["mac"], row["rx_bytes"], row["tx_bytes"]))
    conn.commit()
    conn.close()

def run(url: str, mac: str, csv_path: str = "iface_stats.csv", sqlite_path: str = "",
        user: Optional[str] = None, password: Optional[str] = None,
        insecure: bool = False, timeout: float = 10.0):

    sess = requests.Session()
    headers = {"Accept": "application/json"}
    auth = HTTPBasicAuth(user, password) if user and password else None

    if insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        resp = sess.get(url, headers=headers, auth=auth, timeout=timeout, verify=(not insecure))
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise RuntimeError(f"Chyba při volání {url}: {e}")

    rec = find_mac_record(data, mac)
    if not rec:
        raise ValueError(f"MAC {mac} nebyla nalezena v datech")

    rx, tx = extract_rx_tx(rec)
    ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    row = {"timestamp": ts, "mac": norm_mac(mac), "rx_bytes": rx or "", "tx_bytes": tx or ""}

    if csv_path and csv_path.lower() != "none":
        save_to_csv(csv_path, row)
        print(f"Uloženo do CSV {csv_path}: {row}")

    if sqlite_path:
        save_to_sqlite(sqlite_path, row)
        print(f"Uloženo do SQLite {sqlite_path}")

def main():
    p = argparse.ArgumentParser(description="Stáhne rozhraní a uloží rx/tx bytes pro danou MAC.")
    p.add_argument("--url", default="https://192.168.11.100:34443/rest/interface")
    p.add_argument("--mac", default=TARGET_MAC)
    p.add_argument("--csv", default="iface_stats.csv")
    p.add_argument("--sqlite", default="")
    p.add_argument("--user", default=os.getenv("api"))
    p.add_argument("--password", default=os.getenv("counter"))
    p.add_argument("--insecure", action="store_true")
    p.add_argument("--timeout", type=float, default=10.0)
    args = p.parse_args()

    run(args.url, args.mac, args.csv, args.sqlite, args.user, args.password,
        args.insecure, args.timeout)

if __name__ == "__main__":
    main()
