import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import date

st.set_page_config(
    page_title="TCMB Döviz Mevduat Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("TCMB Döviz Mevduat Dashboard")
st.caption(
    "Kaynak: TCMB EVDS | Yurt içi yerleşiklerin döviz mevduatları"
)

# EVDS seri kodları
SERIES = {
    "Toplam YP Mevduat": "TP.HPBITABLO4.1",
    "Yurt İçi Yerleşikler": "TP.HPBITABLO4.2",
    "Gerçek Kişiler": "TP.HPBITABLO4.3",
    "Tüzel Kişiler": "TP.HPBITABLO4.8",
    "Gerçek Kişiler - Parite Etkisinden Arındırılmış Değişim":
        "TP.HPBITABLO5.2",
    "Tüzel Kişiler - Parite Etkisinden Arındırılmış Değişim":
        "TP.HPBITABLO5.7",
}


def normalize_column(name):
    """Seri kodlarını farklı JSON sütun adlarıyla eşleştirir."""
    return "".join(ch.lower() for ch in str(name) if ch.isalnum())


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_evds_data(start_date, end_date):
    api_key = st.secrets["evds_api_key"]

    series_codes = list(SERIES.values())
    series_string = "-".join(series_codes)

    url = (
        "https://evds3.tcmb.gov.tr/igmevdsms-dis/"
        f"series={series_string}"
        f"&startDate={start_date}"
        f"&endDate={end_date}"
        "&type=json"
    )

    response = requests.get(
        url,
        headers={"key": api_key},
        timeout=60
    )
    response.raise_for_status()

    raw = response.json()

    # API cevabını tabloya dönüştür
    if isinstance(raw, dict):
        if "items" in raw:
            raw = raw["items"]
        elif "data" in raw:
            raw = raw["data"]
        else:
            raise ValueError(
                "EVDS yanıtının biçimi beklenenden farklı."
            )

    df = pd.DataFrame(raw)

    if df.empty:
        raise ValueError(
            "EVDS veri döndürmedi. Tarih aralığını ve seri kodlarını kontrol et."
        )

    # Tarih sütununu bul
    date_col = next(
        (
            col for col in df.columns
            if normalize_column(col) == "tarih"
        ),
        None
    )

    if date_col is None:
        raise ValueError(
            f"Tarih sütunu bulunamadı. Gelen sütunlar: {list(df.columns)}"
        )

    df = df.rename(columns={date_col: "Tarih"})
    df["Tarih"] = pd.to_datetime(
        df["Tarih"],
        dayfirst=True,
        errors="coerce"
    )

    # EVDS seri kodları JSON'da farklı biçimde gelebilir.
    for display_name, code in SERIES.items():
        target = normalize_column(code)

        matching_col = next(
            (
                col for col in df.columns
                if normalize_column(col) == target
            ),
            None
        )

        if matching_col is None:
            raise ValueError(
                f"'{code}' serisi yanıtta bulunamadı. "
                f"Gelen sütunlar: {list(df.columns)}"
            )

        df[display_name] = pd.to_numeric(
            df[matching_col]
            .astype(str)
            .str.replace(",", ".", regex=False),
            errors="coerce"
        )

    df = df.dropna(subset=["Tarih"])
    df = df.sort_values("Tarih").drop_duplicates("Tarih")

    fetched_at = pd.Timestamp.now().strftime("%d.%m.%Y %H:%M")
return df, fetched_at


# Kullanıcı tarih aralığını seçebilir
with st.sidebar:
    st.header("Filtreler")
    start = st.date_input(
        "Başlangıç tarihi",
        value=date(2025, 1, 1),
        min_value=date(2000, 1, 1),
        max_value=date.today()
    )
    end = st.date_input(
        "Bitiş tarihi",
        value=date.today(),
        min_value=date(2000, 1, 1),
        max_value=date.today()
    )

    if st.button("Veriyi yenile"):
        st.cache_data.clear()
        st.rerun()

if start > end:
    st.error("Başlangıç tarihi bitiş tarihinden sonra olamaz.")
    st.stop()

try:
    with st.spinner("TCMB EVDS verileri alınıyor..."):
        df, fetched_at = fetch_evds_data(
    start.strftime("%d-%m-%Y"),
    end.strftime("%d-%m-%Y")
)

except Exception as e:
    st.error("TCMB verileri alınamadı.")
    st.write(
        "Streamlit Secrets, API bağlantısı ve seri kodlarını "
        "kontrol et. Hata ayrıntısı:"
    )
    st.code(str(e))
    st.stop()

if df.empty:
    st.warning("Seçilen tarih aralığında veri bulunamadı.")
    st.stop()

latest = df.iloc[-1]
previous = df.iloc[-2] if len(df) >= 2 else None

st.caption(
    f"Son gözlem tarihi: {latest['Tarih'].strftime('%d.%m.%Y')} "
    f"| Son EVDS kontrolü: {fetched_at} "
    "| Birim: milyon ABD doları"
)

# Üst göstergeler
col1, col2, col3, col4 = st.columns(4)

def show_metric(column, label, series_name):
    value = latest[series_name]

    if pd.isna(value):
        column.metric(label, "Veri yok")
        return

    delta = None
    if previous is not None:
        old_value = previous[series_name]
        if pd.notna(old_value):
            delta = value - old_value

    column.metric(
        label,
        f"{value:,.0f}",
        delta=f"{delta:+,.0f}" if delta is not None else None,
        help="Değerler milyon ABD dolarıdır."
    )


show_metric(col1, "Toplam YP mevduat", "Toplam YP Mevduat")
show_metric(col2, "Yurt içi yerleşikler", "Yurt İçi Yerleşikler")
show_metric(col3, "Gerçek kişiler", "Gerçek Kişiler")
show_metric(col4, "Tüzel kişiler", "Tüzel Kişiler")

st.divider()

# Mevduat seviyeleri
st.subheader("1. Döviz mevduatlarının seyri")

level_choice = st.multiselect(
    "Grafikte gösterilecek seriler",
    [
        "Toplam YP Mevduat",
        "Yurt İçi Yerleşikler",
        "Gerçek Kişiler",
        "Tüzel Kişiler"
    ],
    default=[
        "Gerçek Kişiler",
        "Tüzel Kişiler"
    ]
)

if level_choice:
    fig = px.line(
        df,
        x="Tarih",
        y=level_choice,
        markers=False,
        labels={
            "Tarih": "Tarih",
            "value": "Milyon ABD doları",
            "variable": "Seri"
        }
    )
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

# Haftalık değişimler
st.subheader("2. Parite etkisinden arındırılmış değişim")

st.caption(
    "Bu bölümde EVDS'nin yayımladığı değişim serileri gösterilir. "
    "Değerleri mevduat seviyesiyle karıştırmayın."
)

change_choice = st.multiselect(
    "Değişim serileri",
    [
        "Gerçek Kişiler - Parite Etkisinden Arındırılmış Değişim",
        "Tüzel Kişiler - Parite Etkisinden Arındırılmış Değişim"
    ],
    default=[
        "Gerçek Kişiler - Parite Etkisinden Arındırılmış Değişim",
        "Tüzel Kişiler - Parite Etkisinden Arındırılmış Değişim"
    ]
)

if change_choice:
    change_df = df[["Tarih"] + change_choice].copy()

    fig_change = px.bar(
        change_df,
        x="Tarih",
        y=change_choice,
        barmode="group",
        labels={
            "Tarih": "Tarih",
            "value": "EVDS değeri",
            "variable": "Seri"
        }
    )
    st.plotly_chart(fig_change, use_container_width=True)

# Veri tablosu ve indirme
st.subheader("3. Veri tablosu")

display_df = df[["Tarih"] + list(SERIES.keys())].copy()

# En güncel tarih en üstte
display_df = display_df.sort_values("Tarih", ascending=False)

# Tarihi okunabilir göster
display_df["Tarih"] = display_df["Tarih"].dt.strftime("%d.%m.%Y")

# Sayıları binlik ayraç ve 2 ondalık basamakla göster
for col in SERIES.keys():
    display_df[col] = display_df[col].apply(
        lambda x: f"{x:,.2f}" if pd.notna(x) else "-"
    )

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)

csv = df.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    label="Veriyi CSV olarak indir",
    data=csv,
    file_name="tcmb_doviz_mevduat.csv",
    mime="text/csv"
)

st.caption(
    "Veri kaynağı: TCMB EVDS. "
    "Gösterilen değerler EVDS yanıtından alınır; "
    "son yayımlanan gözlem tarihi yukarıda belirtilmiştir."
)
