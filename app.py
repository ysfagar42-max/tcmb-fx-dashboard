
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="TCMB Döviz Mevduat Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("TCMB Döviz Mevduat Dashboard")
st.caption("Gerçek kişi ve tüzel kişi döviz mevduatları")

st.info(
    "Dashboard arayüzü hazır. "
    "Bir sonraki adımda TCMB EVDS verileri bağlanacak."
)

st.subheader("Örnek görünüm")

sample = pd.DataFrame({
    "Tarih": pd.date_range("2025-01-01", periods=12, freq="MS"),
    "Gerçek kişiler": [
        100, 104, 102, 108, 112, 115,
        114, 120, 123, 125, 129, 132
    ],
    "Tüzel kişiler": [
        80, 82, 85, 84, 89, 91,
        94, 93, 98, 101, 103, 106
    ]
})

sample["Toplam"] = (
    sample["Gerçek kişiler"] + sample["Tüzel kişiler"]
)

left, middle, right = st.columns(3)

left.metric("Toplam mevduat", "238", "+5")
middle.metric("Gerçek kişiler", "132")
right.metric("Tüzel kişiler", "106")

fig = px.line(
    sample,
    x="Tarih",
    y=["Gerçek kişiler", "Tüzel kişiler", "Toplam"],
    title="Mevduatın tarihsel seyri (örnek veri)"
)

st.plotly_chart(fig, use_container_width=True)

st.warning(
    "Gösterilen sayılar yalnızca örnektir; "
    "gerçek TCMB verisi değildir."
)

st.dataframe(sample, use_container_width=True, hide_index=True)
