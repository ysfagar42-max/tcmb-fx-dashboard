
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
            f"Tarih sütunu bulunamadı. Gelen sütunlar: {list(df.columns)}"
        )

    df = df.rename(columns={date_col: "Tarih"})
    df["Tarih"] = pd.to_datetime(
        df["Tarih"],
        dayfirst=True,
        errors="coerce"
    )

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


def figure_to_png(fig, chart_type):
    """Plotly grafiğindeki serileri Matplotlib ile PNG'ye dönüştürür."""
    image, ax = plt.subplots(figsize=(12, 6.5), dpi=160)
    traces = list(fig.data)
    count = len(traces)

    for i, trace in enumerate(traces):
        x = pd.to_datetime(list(trace.x), errors="coerce")
        y = pd.to_numeric(list(trace.y), errors="coerce")

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


def send_dashboard_email(fig, fig_change, latest_date):
    gmail_address = st.secrets["gmail_address"]
    gmail_app_password = st.secrets["gmail_app_password"]
    recipient = "ysfagar42@gmail.com"

    # Chrome gerektirmeyen PNG oluşturma
    chart1_png = figure_to_png(fig, "line")
    chart2_png = figure_to_png(fig_change, "bar")

    msg = EmailMessage()
    msg["Subject"] = (
        f"TCMB Döviz Mevduat Dashboard - {latest_date}"
    )
    msg["From"] = gmail_address
    msg["To"] = recipient

    msg.set_content(
        "TCMB Döviz Mevduat Dashboard\n"
        f"Son gözlem tarihi: {latest_date}\n\n"
        "İlk grafik döviz mevduatlarının seyrini, "
        "ikinci grafik parite etkisinden arındırılmış "
        "değişim serilerini göstermektedir.\n"
        "Veri kaynağı: TCMB EVDS.\n"
        "İki grafik PNG dosyaları olarak eklenmiştir."
    )

    html = f"""
    <html>
      <body>
        <h2>TCMB Döviz Mevduat Dashboard</h2>
        <p><b>Son gözlem tarihi:</b> {latest_date}</p>
        <p>
          İlk grafik, seçilen döviz mevduatı serilerinin
          zaman içindeki seyrini gösterir.
        </p>
        <p>
          İkinci grafik, seçilen parite etkisinden arındırılmış
          değişim serilerini gösterir. Bu değerler mevduat
          seviyesiyle karıştırılmamalıdır.
        </p>
        <p><b>Veri kaynağı:</b> TCMB EVDS.</p>
        <h3>1. Döviz mevduatlarının seyri</h3>
        <img src="cid:chart1" style="width:100%; max-width:900px;">
        <h3>2. Parite etkisinden arındırılmış değişim</h3>
        <img src="cid:chart2" style="width:100%; max-width:900px;">
      </body>
    </html>
    """

    msg.add_alternative(html, subtype="html")
html_part = msg.get_payload()[-1]

    # Grafikleri e-postanın gövdesinde de göster
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

    # PNG dosyalarını ayrıca indirilebilir ek olarak gönder
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

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.starttls()
        server.login(gmail_address, gmail_app_password)
        server.send_message(msg)


# Tarih filtreleri
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
latest_date = latest["Tarih"].strftime("%d.%m.%Y")

st.caption(
    f"Son gözlem tarihi: {latest_date} "
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


# 1. Mevduat seviyeleri
st.subheader("1. Döviz mevduatlarının seyri")

level_choice = st.multiselect(
    "Grafikte gösterilecek seriler",
    [
        "Toplam YP Mevduat",
        "Yurt İçi Yerleşikler",
        "Gerçek Kişiler",
        "Tüzel Kişiler"
    ],
    default=["Gerçek Kişiler", "Tüzel Kişiler"]
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
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)


# 2. Parite etkisinden arındırılmış değişim
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

fig_change = None

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


# E-posta gönderme
st.divider()
st.subheader("Dashboard'u e-posta ile gönder")

st.caption(
    "İki grafik e-posta içinde gösterilir ve PNG dosyaları "
    "olarak ayrıca eklenir. Gönderim yalnızca butona basınca yapılır."
)

if st.button(
    "📧 E-posta ile Gönder",
    disabled=(fig is None or fig_change is None)
):
    try:
        with st.spinner(
            "Grafikler hazırlanıyor ve e-posta gönderiliyor..."
        ):
            send_dashboard_email(fig, fig_change, latest_date)

        st.success(
            "E-posta başarıyla gönderildi: ysfagar42@gmail.com"
        )

    except Exception as e:
        st.error("E-posta gönderilemedi.")
        st.write("Hata ayrıntısı:")
        st.code(str(e))


# Veri tablosu ve CSV indirme
st.subheader("3. Veri tablosu")

display_df = df[["Tarih"] + list(SERIES.keys())].copy()
display_df = display_df.sort_values("Tarih", ascending=False)
display_df["Tarih"] = display_df["Tarih"].dt.strftime("%d.%m.%Y")

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
