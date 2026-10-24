
import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import smtplib

from io import BytesIO
from datetime import date
from email.message import EmailMessage


# ==================================================
# SAYFA AYARLARI
# ==================================================

st.set_page_config(
    page_title="Mevduat Analiz Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("Mevduat Analiz Dashboard")
st.caption("Kaynak: TCMB EVDS")


# ==================================================
# YP DTH SERİLERİ
# ==================================================

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


# ==================================================
# TL MEVDUAT SERİLERİ
# ==================================================

TL_SERIES = {
    "Toplam TL Mevduat": "TP.HPBITABLO3.1",
    "Yurt İçi Yerleşikler": "TP.HPBITABLO3.2",
    "Gerçek Kişiler": "TP.HPBITABLO3.3",
    "Gerçek Kişiler - Vadesiz": "TP.HPBITABLO3.4",
    "Gerçek Kişiler - Vadeli": "TP.HPBITABLO3.5",
    "Ticari Kuruluşlar": "TP.HPBITABLO3.6",
    "Ticari Kuruluşlar - Vadesiz": "TP.HPBITABLO3.7",
    "Ticari Kuruluşlar - Vadeli": "TP.HPBITABLO3.8",
    "Resmî Kuruluşlar": "TP.HPBITABLO3.9",
    "Resmî Kuruluşlar - Vadesiz": "TP.HPBITABLO3.10",
    "Resmî Kuruluşlar - Vadeli": "TP.HPBITABLO3.11",
    "Kâr Amacı Olmayan Kuruluşlar": "TP.HPBITABLO3.12",
    "Kâr Amacı Olmayan Kuruluşlar - Vadesiz": "TP.HPBITABLO3.13",
    "Kâr Amacı Olmayan Kuruluşlar - Vadeli": "TP.HPBITABLO3.14",
    "Banka Dışı Finansal Kuruluşlar": "TP.HPBITABLO3.15",
    "Banka Dışı Finansal Kuruluşlar - Vadesiz": "TP.HPBITABLO3.16",
    "Banka Dışı Finansal Kuruluşlar - Vadeli": "TP.HPBITABLO3.17",
}


# ==================================================
# YARDIMCI FONKSİYONLAR
# ==================================================

def normalize_column(name):
    return "".join(
        ch.lower() for ch in str(name) if ch.isalnum()
    )


def parse_evds_response(raw, series_dict):
    """EVDS yanıtını standart DataFrame'e dönüştürür."""

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

    date_col = next(
        (
            col for col in df.columns
            if normalize_column(col) == "tarih"
        ),
        None
    )

    if date_col is None:
        raise ValueError(
            f"Tarih sütunu bulunamadı. Sütunlar: {list(df.columns)}"
        )

    df = df.rename(columns={date_col: "Tarih"})

    df["Tarih"] = pd.to_datetime(
        df["Tarih"],
        dayfirst=True,
        errors="coerce"
    )

    for display_name, code in series_dict.items():
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

    df = (
        df.dropna(subset=["Tarih"])
        .sort_values("Tarih")
        .drop_duplicates("Tarih")
        .reset_index(drop=True)
    )

    return df


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_evds_data(start_date, end_date, series_items):
    """İstenen EVDS serilerini getirir."""

    api_key = st.secrets["evds_api_key"]
    series_string = "-".join(series_items.values())

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

    return parse_evds_response(
        response.json(),
        series_items
    )


# ==================================================
# GRAFİĞİ PNG'YE DÖNÜŞTÜR
# ==================================================

def figure_to_png(fig, chart_type):
    image, ax = plt.subplots(
        figsize=(12, 6.5),
        dpi=160
    )

    traces = list(fig.data)
    count = len(traces)

    for i, trace in enumerate(traces):
        x = pd.to_datetime(
            list(trace.x),
            errors="coerce"
        )

        y = pd.to_numeric(
            pd.Series(list(trace.y)),
            errors="coerce"
        ).to_numpy()

        if chart_type == "bar":
            dates = mdates.date2num(x.to_pydatetime())
            width = 2.5
            offset = (i - (count - 1) / 2) * width

            ax.bar(
                dates + offset,
                y,
                width=width,
                label=trace.name
            )
        else:
            ax.plot(
                x,
                y,
                label=trace.name,
                linewidth=2
            )

    ax.set_xlabel("Tarih")

    if chart_type == "line":
        ax.set_ylabel("Milyon ABD doları")
        ax.set_title("Döviz mevduatlarının seyri")
    else:
        ax.set_ylabel("EVDS değeri")
        ax.set_title("Parite etkisinden arındırılmış değişim")

    ax.grid(True, alpha=0.25)
    ax.legend()

    ax.xaxis.set_major_formatter(
        mdates.DateFormatter("%d.%m.%Y")
    )

    image.autofmt_xdate()
    image.tight_layout()

    output = BytesIO()

    image.savefig(
        output,
        format="png",
        dpi=160,
        bbox_inches="tight"
    )

    plt.close(image)

    return output.getvalue()


# ==================================================
# E-POSTA GÖNDERME — MEVCUT YP DTH ÖZELLİĞİ
# ==================================================

def send_dashboard_email(fig, fig_change, latest_date):
    gmail_address = st.secrets["gmail_address"]
    gmail_app_password = st.secrets["gmail_app_password"]

    recipient = "ysfagar42@gmail.com"

    chart1_png = figure_to_png(fig, "line")
    chart2_png = figure_to_png(fig_change, "bar")

    msg = EmailMessage()

    msg["Subject"] = (
        f"YP DTH Dashboard - {latest_date}"
    )
    msg["From"] = gmail_address
    msg["To"] = recipient

    msg.set_content(
        "YP DTH Dashboard\n"
        f"Son gözlem tarihi: {latest_date}\n\n"
        "Grafikler PNG olarak ektedir.\n"
        "Veri kaynağı: TCMB EVDS."
    )

    html = f"""
    <html>
      <body>
        <h2>YP DTH Dashboard</h2>
        <p><b>Son gözlem tarihi:</b> {latest_date}</p>
        <p>Veri kaynağı: TCMB EVDS.</p>

        <h3>1. Döviz mevduatlarının seyri</h3>
        <img src="cid:chart1" style="width:100%; max-width:900px;">

        <h3>2. Parite etkisinden arındırılmış değişim</h3>
        <img src="cid:chart2" style="width:100%; max-width:900px;">
      </body>
    </html>
    """

    msg.add_alternative(html, subtype="html")
    html_part = msg.get_payload()[-1]

    html_part.add_related(
        chart1_png,
        maintype="image",
        subtype="png",
        cid="<chart1>",
        filename="doviz_mevduat_seviyesi.png",
        disposition="inline"
    )

    html_part.add_related(
        chart2_png,
        maintype="image",
        subtype="png",
        cid="<chart2>",
        filename="parite_etkisinden_arindirilmis_degisim.png",
        disposition="inline"
    )

    msg.add_attachment(
        chart1_png,
        maintype="image",
        subtype="png",
        filename="doviz_mevduat_seviyesi.png"
    )

    msg.add_attachment(
        chart2_png,
        maintype="image",
        subtype="png",
        filename="parite_etkisinden_arindirilmis_degisim.png"
    )

    with smtplib.SMTP(
        "smtp.gmail.com",
        587,
        timeout=30
    ) as server:
        server.starttls()
        server.login(
            gmail_address,
            gmail_app_password
        )
        server.send_message(msg)


# ==================================================
# ANA MENÜ
# ==================================================

page_choice = st.radio(
    "Analiz ekranı",
    ["YP DTH", "TL Mevduat"],
    horizontal=True,
    key="dashboard_choice"
)

st.divider()


# ==================================================
# ORTAK TARİH FİLTRELERİ
# ==================================================

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


start_str = start.strftime("%d-%m-%Y")
end_str = end.strftime("%d-%m-%Y")


# ==================================================
# TL MEVDUAT PANELİ
# ==================================================

if page_choice == "TL Mevduat":

    st.header("TL Mevduat Analizi")

    st.caption(
        "Kaynak: TCMB EVDS | TL mevduat seviyeleri ve müşteri kırılımları"
    )

    try:
        with st.spinner("TL mevduat verileri alınıyor..."):
            tl_df = fetch_evds_data(
                start_str,
                end_str,
                TL_SERIES
            )

    except Exception as e:
        st.error("TL mevduat verileri alınamadı.")
        st.write(
            "EVDS API bağlantısını, seri kodlarını ve Secrets ayarlarını kontrol et."
        )
        st.code(str(e))
        st.stop()

    if tl_df.empty:
        st.warning("Seçilen tarih aralığında veri bulunamadı.")
        st.stop()

    # EVDS düzey serileri milyon TL ise milyar TL'ye çevir.
    # İlk çalıştırmada EVDS'nin seri birimini doğrula.
    tl_value_columns = list(TL_SERIES.keys())

    tl_df[tl_value_columns] = (
        tl_df[tl_value_columns] / 1000
    )

    total_col = "Toplam TL Mevduat"

    # Haftalık ve çok haftalı değişimler
    tl_df["Haftalık Değişim"] = tl_df[total_col].diff()

    tl_df["Haftalık Değişim (%)"] = (
        tl_df[total_col].pct_change() * 100
    )

    tl_df["4 Haftalık Değişim"] = (
        tl_df[total_col] - tl_df[total_col].shift(4)
    )

    tl_df["4 Haftalık Değişim (%)"] = (
        tl_df[total_col].pct_change(4) * 100
    )

    tl_df["13 Haftalık Değişim"] = (
        tl_df[total_col] - tl_df[total_col].shift(13)
    )

    tl_df["13 Haftalık Değişim (%)"] = (
        tl_df[total_col].pct_change(13) * 100
    )

    latest_tl = tl_df.iloc[-1]
    previous_tl = (
        tl_df.iloc[-2] if len(tl_df) >= 2 else None
    )

    latest_date_tl = latest_tl["Tarih"].strftime("%d.%m.%Y")

    st.caption(
        f"Son gözlem tarihi: {latest_date_tl} | "
        "Gösterim birimi: milyar TL"
    )

    # Üst KPI kartları
    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Toplam TL mevduat",
        f"{latest_tl[total_col]:,.1f}"
    )

    c2.metric(
        "Haftalık değişim",
        (
            f"{latest_tl['Haftalık Değişim']:+,.1f} mlr TL"
            if pd.notna(latest_tl["Haftalık Değişim"])
            else "Veri yok"
        )
    )

    c3.metric(
        "Haftalık değişim (%)",
        (
            f"{latest_tl['Haftalık Değişim (%)']:+.2f}%"
            if pd.notna(latest_tl["Haftalık Değişim (%)"])
            else "Veri yok"
        )
    )

    c4.metric(
        "Yurt içi yerleşikler",
        f"{latest_tl['Yurt İçi Yerleşikler']:,.1f}"
    )

    st.divider()

    # Müşteri grupları
    st.subheader("Müşteri gruplarına göre TL mevduat")

    segment_columns = [
        "Gerçek Kişiler",
        "Ticari Kuruluşlar",
        "Resmî Kuruluşlar",
        "Kâr Amacı Olmayan Kuruluşlar",
        "Banka Dışı Finansal Kuruluşlar"
    ]

    selected_segments = st.multiselect(
        "Grafikte gösterilecek gruplar",
        segment_columns,
        default=[
            "Gerçek Kişiler",
            "Ticari Kuruluşlar"
        ],
        key="tl_segments"
    )

    if selected_segments:
        segment_fig = px.line(
            tl_df,
            x="Tarih",
            y=selected_segments,
            markers=False,
            labels={
                "Tarih": "Tarih",
                "value": "Milyar TL",
                "variable": "Müşteri grubu"
            }
        )

        segment_fig.update_layout(
            hovermode="x unified"
        )

        st.plotly_chart(
            segment_fig,
            use_container_width=True
        )

    # Vadeli / vadesiz analiz
    st.divider()
    st.subheader("Vadeli ve vadesiz mevduat")

    deposit_type_columns = [
        "Gerçek Kişiler - Vadesiz",
        "Gerçek Kişiler - Vadeli",
        "Ticari Kuruluşlar - Vadesiz",
        "Ticari Kuruluşlar - Vadeli",
        "Resmî Kuruluşlar - Vadesiz",
        "Resmî Kuruluşlar - Vadeli",
        "Kâr Amacı Olmayan Kuruluşlar - Vadesiz",
        "Kâr Amacı Olmayan Kuruluşlar - Vadeli",
        "Banka Dışı Finansal Kuruluşlar - Vadesiz",
        "Banka Dışı Finansal Kuruluşlar - Vadeli"
    ]

    selected_types = st.multiselect(
        "Mevduat türlerini seç",
        deposit_type_columns,
        default=[
            "Gerçek Kişiler - Vadeli",
            "Gerçek Kişiler - Vadesiz",
            "Ticari Kuruluşlar - Vadeli",
            "Ticari Kuruluşlar - Vadesiz"
        ],
        key="tl_deposit_types"
    )

    if selected_types:
        type_fig = px.line(
            tl_df,
            x="Tarih",
            y=selected_types,
            labels={
                "Tarih": "Tarih",
                "value": "Milyar TL",
                "variable": "Mevduat türü"
            }
        )

        type_fig.update_layout(
            hovermode="x unified"
        )

        st.plotly_chart(
            type_fig,
            use_container_width=True
        )

    # Değişim tablosu
    st.divider()
    st.subheader("Toplam TL mevduat değişim tablosu")

    change_columns = [
        "Tarih",
        "Toplam TL Mevduat",
        "Haftalık Değişim",
        "Haftalık Değişim (%)",
        "4 Haftalık Değişim",
        "4 Haftalık Değişim (%)",
        "13 Haftalık Değişim",
        "13 Haftalık Değişim (%)"
    ]

    change_table = (
        tl_df[change_columns]
        .sort_values("Tarih", ascending=False)
        .copy()
    )

    change_table["Tarih"] = (
        change_table["Tarih"].dt.strftime("%d.%m.%Y")
    )

    st.dataframe(
        change_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Toplam TL Mevduat": st.column_config.NumberColumn(
                "Toplam TL Mevduat (mlr TL)",
                format="%.2f"
            ),
            "Haftalık Değişim": st.column_config.NumberColumn(
                "Haftalık Değişim (mlr TL)",
                format="%+.2f"
            ),
            "Haftalık Değişim (%)": st.column_config.NumberColumn(
                "Haftalık Değişim (%)",
                format="%+.2f%%"
            ),
            "4 Haftalık Değişim": st.column_config.NumberColumn(
                "4 Haftalık Değişim (mlr TL)",
                format="%+.2f"
            ),
            "4 Haftalık Değişim (%)": st.column_config.NumberColumn(
                "4 Haftalık Değişim (%)",
                format="%+.2f%%"
            ),
            "13 Haftalık Değişim": st.column_config.NumberColumn(
                "13 Haftalık Değişim (mlr TL)",
                format="%+.2f"
            ),
            "13 Haftalık Değişim (%)": st.column_config.NumberColumn(
                "13 Haftalık Değişim (%)",
                format="%+.2f%%"
            )
        }
    )

    # Tüm seri seviyeleri
    st.subheader("Tüm TL mevduat serileri")

    level_table = (
        tl_df[["Tarih"] + tl_value_columns]
        .sort_values("Tarih", ascending=False)
        .copy()
    )

    level_table["Tarih"] = (
        level_table["Tarih"].dt.strftime("%d.%m.%Y")
    )

    st.dataframe(
        level_table,
        use_container_width=True,
        hide_index=True
    )

    csv_data = tl_df.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "TL mevduat verisini CSV olarak indir",
        data=csv_data,
        file_name="tcmb_tl_mevduat.csv",
        mime="text/csv",
        key="download_tl_csv"
    )

    st.caption(
        "Kaynak: TCMB EVDS. Haftalık değişim bir önceki gözleme, "
        "4 ve 13 haftalık değişimler sırasıyla 4 ve 13 gözlem geriye "
        "göre hesaplanır."
    )

    st.stop()


# ==================================================
# YP DTH PANELİ — MEVCUT PANEL
# ==================================================

st.header("YP DTH Analizi")

st.caption(
    "Kaynak: TCMB EVDS | Yurt içi yerleşiklerin döviz mevduatları"
)

try:
    with st.spinner("TCMB EVDS verileri alınıyor..."):
        df = fetch_evds_data(
            start_str,
            end_str,
            SERIES
        )

except Exception as e:
    st.error("TCMB verileri alınamadı.")

    st.write(
        "Streamlit Secrets, API bağlantısı ve seri kodlarını kontrol et."
    )

    st.code(str(e))
    st.stop()


if df.empty:
    st.warning("Seçilen tarih aralığında veri bulunamadı.")
    st.stop()


latest = df.iloc[-1]
previous = df.iloc[-2] if len(df) >= 2 else None

latest_date = latest["Tarih"].strftime("%d.%m.%Y")

st.caption(
    f"Son gözlem tarihi: {latest_date} "
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


# Döviz mevduatlarının seyri

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
    ],
    key="yp_level_choice"
)

fig = None

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

    fig.update_layout(
        hovermode="x unified"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# Parite etkisinden arındırılmış değişim

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
    ],
    key="yp_change_choice"
)

fig_change = None

if change_choice:
    change_df = df[
        ["Tarih"] + change_choice
    ].copy()

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

    st.plotly_chart(
        fig_change,
        use_container_width=True
    )


# E-posta butonu

st.divider()
st.subheader("Dashboard'u e-posta ile gönder")

st.caption(
    "İki grafik e-posta içinde gösterilir ve PNG dosyaları "
    "olarak ayrıca eklenir."
)

if st.button(
    "📧 E-posta ile Gönder",
    disabled=(fig is None or fig_change is None),
    key="send_yp_email"
):
    try:
        with st.spinner(
            "Grafikler hazırlanıyor ve e-posta gönderiliyor..."
        ):
            send_dashboard_email(
                fig,
                fig_change,
                latest_date
            )

        st.success("E-posta başarıyla gönderildi.")

    except Exception as e:
        st.error("E-posta gönderilemedi.")
        st.code(str(e))


# Veri tablosu ve CSV

st.subheader("3. Veri tablosu")

display_df = df[
    ["Tarih"] + list(SERIES.keys())
].copy()

display_df = display_df.sort_values(
    "Tarih",
    ascending=False
)

display_df["Tarih"] = display_df["Tarih"].dt.strftime(
    "%d.%m.%Y"
)

for col in SERIES.keys():
    display_df[col] = display_df[col].apply(
        lambda x: f"{x:,.2f}" if pd.notna(x) else "-"
    )

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)

csv = df.to_csv(
    index=False
).encode("utf-8-sig")

st.download_button(
    label="Veriyi CSV olarak indir",
    data=csv,
    file_name="tcmb_yp_dth.csv",
    mime="text/csv",
    key="download_yp_csv"
)

st.caption(
    "Veri kaynağı: TCMB EVDS. "
    "Son yayımlanan gözlem tarihi yukarıda belirtilmiştir."
)
