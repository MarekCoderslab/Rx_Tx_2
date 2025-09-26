import pandas as pd

BYTES_IN_MB = 1048576

df_counter = pd.read_csv("iface_stats.csv")
df_counter["rx_MB"] = df_counter["rx_bytes"].fillna(0).astype(float) / BYTES_IN_MB
df_counter["tx_MB"] = df_counter["tx_bytes"].fillna(0).astype(float) / BYTES_IN_MB
df_counter["delta_rx_MB"] = df_counter["rx_MB"].diff().fillna(0)
df_counter["delta_tx_MB"] = df_counter["tx_MB"].diff().fillna(0)

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

st.title("Přenos dat Palackého 209")
st.subheader("Pilový graf  RX toku s výpočtem MB/hod")

# Převod timestamp
df_counter["timestamp"] = pd.to_datetime(df_counter["timestamp"])

# Výpočet tabulky s podílem MB/hod
rows = []
fig, ax = plt.subplots(figsize=(10, 5))

for i in range(1, len(df_counter)):
    t_prev = df_counter["timestamp"].iloc[i - 1]
    t_curr = df_counter["timestamp"].iloc[i]
    rx = df_counter["delta_rx_MB"].iloc[i]

    delta_hours = (t_curr - t_prev).total_seconds() / 3600
    mb_per_hour = rx / delta_hours if delta_hours > 0 else None

    # Zub: náběh z nuly, pád zpět
    ax.plot([t_prev, t_curr, t_curr], [0, rx, 0], color="blue", linewidth=1.5)

    # Anotace nad vrcholem
    if mb_per_hour is not None:
        ax.annotate(
            f"{mb_per_hour:.1f}",
            xy=(t_curr, rx),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color="blue"
        )

    # Tabulka
    rows.append({
        "start_time": t_prev.strftime("%d.%m.%y %H:%M"),
        "end_time": t_curr.strftime("%d.%m.%y %H:%M"),
        "delta_rx_MB": rx,
        "delta_hours": round(delta_hours, 2),
        "MB_per_hour": round(mb_per_hour, 1)
    })

# Finalizace grafu
ax.set_title("Pilový graf RX s podílem MB/hod")
ax.set_xlabel("Čas")
ax.set_ylabel("Příchozí data [MB]")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m. %H:%M"))
plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
ax.grid(True, linestyle="--", alpha=0.5)
st.pyplot(fig)

# Zobrazení tabulky
df_rx_table = pd.DataFrame(rows)
# Obrácení pořadí
df_rx_table = df_rx_table.iloc[::-1]
st.subheader("Tabulka výpočtu MB/hod")
st.dataframe(df_rx_table)
