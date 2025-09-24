import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
# from datetime import datetime
from datetime import datetime, timedelta

import requests
import urllib3
from requests.auth import HTTPBasicAuth
import os
import csv
import sqlite3

# --- Nastavení ---
url = "https://192.168.11.100:34443/rest/interface"
user = "api"
password = "counters"
TARGET_MAC = "D4:CA:6D:9E:F8:A0"
BYTES_IN_MB = 1048576

# --- Funkce pro API ---
def norm_mac(mac: str) -> str:
    s = mac.strip().upper().replace("-", ":").replace(".", "").replace(" ", "")
    if ":" not in s and len(s) == 12:
        s = ":".join(s[i:i+2] for i in range(0, 12, 2))
    return s

def find_mac_record(data, target_mac):
    MAC_KEYS = {"mac-address", "macAddress", "mac", "hwaddr"}
    target = norm_mac(target_mac)
    for item in data:
        for mk in MAC_KEYS:
            if mk in item and norm_mac(str(item[mk])) == target:
                return item
    return None

def extract_rx_tx(record):
    RX_KEYS = {"rx-byte", "fp-rx-byte", "rxBytes", "rx_bytes"}
    TX_KEYS = {"tx-byte", "fp-tx-byte", "txBytes", "tx_bytes"}
    rx = tx = 0
    for k in RX_KEYS:
        if k in record:
            rx = int(record[k])
            break
    for k in TX_KEYS:
        if k in record:
            tx = int(record[k])
            break
    return rx, tx

def fetch_and_save():
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    resp = requests.get(url, auth=HTTPBasicAuth(user, password), verify=False)
    data = resp.json()
    rec = find_mac_record(data, TARGET_MAC)
    if not rec:
        st.error("MAC adresa nebyla nalezena.")
        return None
    rx, tx = extract_rx_tx(rec)
    # ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    ts = (datetime.utcnow() + timedelta(hours=2)).isoformat(timespec="seconds") + "Z"

    row = {"timestamp": ts, "mac": norm_mac(TARGET_MAC), "rx_bytes": rx, "tx_bytes": tx}

    # Uložení do CSV
    csv_path = "iface_stats.csv"
    header = ["timestamp", "mac", "rx_bytes", "tx_bytes"]
    exists = os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not exists:
            writer.writeheader()
        writer.writerow(row)

    return row


# --- Streamlit UI ---
st.title("📡 Přenos dat z antény – Chva209")

if st.button("📥 Načíst aktuální data z API"):
    row = fetch_and_save()
    if row:
        st.success(f"Uloženo: {row}")



# --- Načtení a zpracování dat ---
if os.path.exists("iface_stats.csv"):
    df = pd.read_csv("iface_stats.csv")
    df["rx_MB"] = df["rx_bytes"].fillna(0).astype(float) / BYTES_IN_MB
    df["tx_MB"] = df["tx_bytes"].fillna(0).astype(float) / BYTES_IN_MB
    df["delta_rx_MB"] = df["rx_MB"].diff().fillna(0)
    df["delta_tx_MB"] = df["tx_MB"].diff().fillna(0)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    print(df["timestamp"].dtype)

    st.subheader("📊 Poslední záznamy")
    # změna formátu datumu
    df_display = df.copy()
    df_display["timestamp"] = df_display["timestamp"].dt.strftime("%d.%m.%y %H:%M")
    # Zaokrouhlení na 1 desetinné místo
    df_display["delta_rx_MB"] = df_display["delta_rx_MB"].round(1)
    df_display["delta_tx_MB"] = df_display["delta_tx_MB"].round(1)
    # Přidej pořadí (index) jako nový sloupec
    df_display["row_id"] = range(len(df_display))
    # Vygeneruj HTML tabulku
    # html_table = df_display[["row_id", "timestamp", "delta_rx_MB", "delta_tx_MB"]].tail(5).to_html(index=False)
    
    df_tail = df_display[["timestamp", "delta_rx_MB", "delta_tx_MB"]].tail(5).reset_index(drop=True)
    html_table = df_tail.to_html(index=False)

    # Přepiš zarovnání v <th> i <td>
    html_table = html_table.replace('text-align: right;', 'text-align: center !important;')
    html_table = html_table.replace('text-align: left;', 'text-align: center !important;')
    
    # Styl tabulky
    st.markdown("""
    <style>
    table {
        width: 100%;
        border-collapse: collapse;
        font-family: sans-serif;
    }
    th {
        text-align: center !important;
        padding: 8px;
        background-color: #e0e0e0;
        border-bottom: 2px solid #ccc;
    }
    td {
        text-align: center;
        padding: 6px;
        border-bottom: 1px solid #eee;
    }
    tr:hover {
        background-color: #f9f9f9;
    }
    """, unsafe_allow_html=True)
    
    st.markdown(html_table, unsafe_allow_html=True)
    
    # Získání timestampu z tabulky
    reference_ts_str = df_tail["timestamp"].iloc[0]

    # Převedení na datetime + časové pásmo
    reference_ts = pd.to_datetime(reference_ts_str, format="%d.%m.%y %H:%M")
    if reference_ts.tzinfo is None:
        reference_ts = reference_ts.tz_localize("UTC")
    else:
        reference_ts = reference_ts.tz_convert("UTC")

    # Posun o −1 hodinu
    line_ts = reference_ts - pd.Timedelta(hours=1)

    line_x = mdates.date2num(line_ts)

    # --- Graf ---
    fig, ax1 = plt.subplots(figsize=(10, 5))
    x = mdates.date2num(df["timestamp"])
    bar_width = 0.02
    # Ulož si RX a TX hodnoty
    rx = df["delta_rx_MB"]
    tx = df["delta_tx_MB"]

    ax1.bar(x - bar_width/2, rx, width=bar_width, color="blue", alpha=0.7, label="RX")
    ax1.set_ylabel("Příchozí data [MB]", color="blue")
    ax1.tick_params(axis="y", labelcolor="blue")
    ax1.axvline(
        x=line_x,
        color="gray",
        linestyle="--",
        linewidth=1.5,
        label="-1h od prvního záznamu"
)

    ax2 = ax1.twinx()
    ax2.bar(x + bar_width/2, tx, width=bar_width, color="red", alpha=0.7, label="TX")
    ax2.set_ylabel("Odchozí data [MB]", color="red")
    ax2.tick_params(axis="y", labelcolor="red")
    

   # Označ bod v grafu
    # ax1.bar(x[highlight_idx] - bar_width/2, rx.iloc[highlight_idx], width=bar_width, color="darkblue", label="RX (označený)", alpha=1)
    # ax2.bar(x[highlight_idx] + bar_width/2, tx.iloc[highlight_idx], width=bar_width, color="darkred", alpha=1, bottom=rx.iloc[highlight_idx])###

    ax1.set_ylim(0, 200)     # RX osa: 0 až 200 MB
    ax2.set_ylim(0, 2000)    # TX osa: 0 až 2000 MB
    
    ax1.xaxis_date()
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m. %H:%M"))
    plt.setp(ax1.get_xticklabels(), rotation=45, ha="right")
    ax1.grid(True, axis="y", linestyle="--", alpha=0.5)
    plt.title("Přenos dat v čase Palackého 209")
    plt.tight_layout()

    st.pyplot(fig)
else:
    st.warning("Soubor iface_stats.csv zatím neexistuje. Načti data z API.")

import csv

BYTES_IN_MB = 1048576  # 1 MB = 1024*1024 B

input_file = "iface_stats.csv"
output_file = "rozdily_counter.csv"

with open(input_file, newline="", encoding="utf-8") as f_in, \
     open(output_file, "w", newline="", encoding="utf-8") as f_out:

    reader = csv.DictReader(f_in)
    fieldnames = ["timestamp", "mac", "rx_MB", "tx_MB", "delta_rx_MB", "delta_tx_MB"]
    writer = csv.DictWriter(f_out, fieldnames=fieldnames)
    writer.writeheader()

    prev_rx = prev_tx = 0
    for row in reader:
        # převod bytes na MB
        rx_bytes = float(row.get("rx_bytes", 0) or 0)
        tx_bytes = float(row.get("tx_bytes", 0) or 0)
        rx_MB = rx_bytes / BYTES_IN_MB
        tx_MB = tx_bytes / BYTES_IN_MB

        # výpočet delta oproti předchozímu řádku
        delta_rx = rx_MB - prev_rx
        delta_tx = tx_MB - prev_tx

        writer.writerow({
            "timestamp": row.get("timestamp", ""),
            "mac": row.get("mac", ""),
            "rx_MB": round(rx_MB, 2),
            "tx_MB": round(tx_MB, 2),
            "delta_rx_MB": round(delta_rx, 2),
            "delta_tx_MB": round(delta_tx, 2)
        })

        # uložit aktuální hodnoty pro delta v dalším řádku
        prev_rx = rx_MB
        prev_tx = tx_MB


# Kombo box s timestamp

# CSS pro zúžení selectboxu
st.markdown("""
    <style>
    div[data-baseweb="select"] {
        max-width: 250px;
    }
    </style>
""", unsafe_allow_html=True)

# Formátovaný timestamp jako text
timestamps_str = df["timestamp"].dt.strftime("%d.%m.%Y %H:%M")

# Selectbox s užší šířkou
selected_time_str = st.selectbox("Vyber čas záznamu", options=timestamps_str)

# Najdi odpovídající index v DataFrame
index = df[df["timestamp"].dt.strftime("%d.%m.%Y %H:%M") == selected_time_str].index[0]

# index = st.selectbox(
#     "Vyber čas záznamu",
#     options=df["timestamp"].dt.strftime("%d.%m.%Y %H:%M")
# )

           
if st.button("📍 Zobrazit vybraný záznam"):
    formatted_ts = df["timestamp"].iloc[index].strftime("%d.%m.%y %H:%M")
    rx_val = round(df["delta_rx_MB"].iloc[index], 2)
    tx_val = round(df["delta_tx_MB"].iloc[index], 2)

    st.write(f"🕒 Čas: {formatted_ts}")
    st.write(f"📦 RX: {rx_val} MB")
    st.write(f"📤 TX: {tx_val} MB")


