import smtplib
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io

from email.message import EmailMessage
from datetime import date, datetime, timedelta


# =========================================================
# SAYFA AYARLARI
# =========================================================

st.set_page_config(
    page_title="Mevduat Analiz Dashboard",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2.2rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }
    h1 {
        letter-spacing: -0.035em;
        font-weight: 750 !important;
    }
    h2, h3 {
        letter-spacing: -0.02em;
        font-weight: 650 !important;
    }
    div[data-testid="stMetric"] {
        background: rgba(128, 128, 128, 0.055);
        border: 1px solid rgba(128, 128, 128, 0.18);
        border-radius: 14px;
        padding: 14px 16px;
    }
    div[data-testid="stMetricLabel"] {
        font-weight: 600;
    }
    div[data-testid="stPlotlyChart"] {
        border: 1px solid rgba(128, 128, 128, 0.15);
        border-radius: 14px;
        padding: 8px 8px 2px 8px;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid rgba(128, 128, 128, 0.15);
        border-radius: 12px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Mevduat Piyasası | Analiz Paneli")
st.caption(
    "TCMB EVDS verileriyle TL ve yabancı para mevduatlarının "
    "seviyesini, haftalık hareketlerini ve değişim bileşenlerini takip edin."
)


# =========================================================
# SECRETS
# =========================================================

try:
    EVDS_API_KEY = st.secrets["evds_api_key"]
    GMAIL_ADDRESS = st.secrets["gmail_address"]
    GMAIL_APP_PASSWORD = st.secrets["gmail_app_password"]
except Exception:
    st.error(
        "Gerekli Secrets bilgileri bulunamadı. "
        "evds_api_key, gmail_address ve gmail_app_password "
        "tanımlarını kontrol et."
    )
    st.stop()

EMAIL_RECIPIENT = "ysfagar42@gmail.com"


# =========================================================
# YP DTH SERİLERİ
# =========================================================

YP_LEVEL_SERIES = {
    "Toplam YP Mevduat": "TP.HPBITABLO4.1",
    "Yurt İçi Yerleşikler": "TP.HPBITABLO4.2",
    "Gerçek Kişiler": "TP.HPBITABLO4.3",
    "Gerçek Kişiler - USD": "TP.HPBITABLO4.4",
    "Gerçek Kişiler - EUR": "TP.HPBITABLO4.5",
    "Gerçek Kişiler - Diğer Döviz": "TP.HPBITABLO4.6",
    "Gerçek Kişiler - Altın": "TP.HPBITABLO4.7",
    "Tüzel Kişiler": "TP.HPBITABLO4.8",
    "Tüzel Kişiler - USD": "TP.HPBITABLO4.9",
    "Tüzel Kişiler - EUR": "TP.HPBITABLO4.10",
    "Tüzel Kişiler - Diğer Döviz": "TP.HPBITABLO4.11",
    "Tüzel Kişiler - Altın": "TP.HPBITABLO4.12",
    "Yurt İçi Yerleşik Bankalar": "TP.HPBITABLO4.13",
    "Yurt Dışı Yerleşikler": "TP.HPBITABLO4.16",
    "Yurt Dışı Yerleşikler - USD": "TP.HPBITABLO4.17",
    "Yurt Dışı Yerleşikler - EUR": "TP.HPBITABLO4.18",
    "Yurt Dışı Yerleşikler - Diğer Döviz": "TP.HPBITABLO4.19",
    "Yurt Dışı Yerleşikler - Altın": "TP.HPBITABLO4.20",
    "Yurt Dışı Yerleşik Bankalar": "TP.HPBITABLO4.21",
}

YP_CHANGE_SERIES = {
    "Parite Hariç - Yurt İçi Yerleşikler": "TP.HPBITABLO5.1",
    "Parite Hariç - Gerçek Kişiler": "TP.HPBITABLO5.2",
    "Parite Hariç - Gerçek Kişiler USD": "TP.HPBITABLO5.3",
    "Parite Hariç - Gerçek Kişiler EUR": "TP.HPBITABLO5.4",
    "Parite Hariç - Gerçek Kişiler Diğer Döviz": "TP.HPBITABLO5.5",
    "Parite Hariç - Gerçek Kişiler Altın": "TP.HPBITABLO5.6",
    "Parite Hariç - Tüzel Kişiler": "TP.HPBITABLO5.7",
    "Parite Hariç - Tüzel Kişiler USD": "TP.HPBITABLO5.8",
    "Parite Hariç - Tüzel Kişiler EUR": "TP.HPBITABLO5.9",
    "Parite Hariç - Tüzel Kişiler Diğer Döviz": "TP.HPBITABLO5.10",
    "Parite Hariç - Tüzel Kişiler Altın": "TP.HPBITABLO5.11",
    "Parite Etkisi - Yurt İçi Yerleşikler": "TP.HPBITABLO5.12",
    "Parite Etkisi - Gerçek Kişiler": "TP.HPBITABLO5.13",
    "Parite Etkisi - Gerçek Kişiler USD": "TP.HPBITABLO5.14",
    "Parite Etkisi - Gerçek Kişiler EUR": "TP.HPBITABLO5.15",
    "Parite Etkisi - Gerçek Kişiler Diğer Döviz": "TP.HPBITABLO5.16",
    "Parite Etkisi - Gerçek Kişiler Altın": "TP.HPBITABLO5.17",
    "Parite Etkisi - Tüzel Kişiler": "TP.HPBITABLO5.18",
    "Parite Etkisi - Tüzel Kişiler USD": "TP.HPBITABLO5.19",
    "Parite Etkisi - Tüzel Kişiler EUR": "TP.HPBITABLO5.20",
    "Parite Etkisi - Tüzel Kişiler Diğer Döviz": "TP.HPBITABLO5.21",
    "Parite Etkisi - Tüzel Kişiler Altın": "TP.HPBITABLO5.22",
}


# =========================================================
# TL MEVDUAT SERİLERİ
# =========================================================

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


# =========================================================
# GRAFİK RENKLERİ
# =========================================================

COLORS = {
    "Toplam YP Mevduat": "#263B5A",
    "Gerçek Kişiler": "#247BA0",
    "Tüzel Kişiler": "#F28E2B",
    "Yurt İçi Yerleşikler": "#59A14F",
}

SEGMENT_COLORS = {
    "Gerçek Kişiler": "#247BA0",
    "Tüzel Kişiler": "#F28E2B",
}


# =========================================================
# YARDIMCI FONKSİYONLAR
# =========================================================

def normalize_column(value):
    return (
        str(value)
        .strip()
        .replace("\ufeff", "")
        .replace(" ", "")
        .replace(".", "")
        .replace("_", "")
        .lower()
    )


def parse_evds_response(raw, series_dict):
    if isinstance(raw, dict):
        if "items" in raw:
            raw = raw["items"]
        elif "data" in raw:
            raw = raw["data"]
        else:
            raise ValueError(
                f"EVDS beklenmeyen yanıt döndürdü: {str(raw)[:300]}"
            )

    df = pd.DataFrame(raw)

    if df.empty:
        raise ValueError("EVDS veri döndürmedi.")

    date_candidates = [
        c for c in df.columns
        if normalize_column(c) in ("tarih", "date")
    ]

    date_col = date_candidates[0] if date_candidates else df.columns[0]
    df = df.rename(columns={date_col: "Tarih"})

    df["Tarih"] = pd.to_datetime(
        df["Tarih"],
        dayfirst=True,
        errors="coerce",
    )

    normalized_columns = {
        normalize_column(c): c for c in df.columns
    }

    rename_map = {}

    for display_name, series_code in series_dict.items():
        normalized_code = normalize_column(series_code)

        if normalized_code in normalized_columns:
            rename_map[normalized_columns[normalized_code]] = display_name

    df = df.rename(columns=rename_map)

    for display_name in series_dict:
        if display_name in df.columns:
            df[display_name] = pd.to_numeric(
                df[display_name]
                .astype(str)
                .str.replace(",", ".", regex=False),
                errors="coerce",
            )

    return (
        df.dropna(subset=["Tarih"])
        .sort_values("Tarih")
        .drop_duplicates(subset=["Tarih"], keep="last")
        .reset_index(drop=True)
    )


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_evds_data(start_date, end_date, series_items):
    """EVDS verilerini gruplar halinde çeker ve son çekim zamanını saklar."""
    series_dict = dict(series_items)
    series_list = list(series_dict.items())
    frames = []

    for i in range(0, len(series_list), 10):
        chunk = dict(series_list[i:i + 10])
        series_string = "-".join(chunk.values())

        url = (
            "https://evds3.tcmb.gov.tr/igmevdsms-dis/"
            f"series={series_string}"
            f"&startDate={start_date}"
            f"&endDate={end_date}"
            "&type=json"
        )

        response = requests.get(
            url,
            headers={"key": EVDS_API_KEY},
            timeout=60,
        )
        response.raise_for_status()

        frames.append(parse_evds_response(response.json(), chunk))

    if not frames:
        raise ValueError("EVDS'den veri alınamadı.")

    result = frames[0]

    for frame in frames[1:]:
        new_columns = [
            c for c in frame.columns
            if c != "Tarih" and c not in result.columns
        ]

        result = result.merge(
            frame[["Tarih"] + new_columns],
            on="Tarih",
            how="outer",
        )

    result = result.sort_values("Tarih").reset_index(drop=True)

    fetched_at = datetime.now().astimezone().strftime(
        "%d.%m.%Y %H:%M:%S %Z"
    )

    return result, fetched_at


def show_data_status(df, fetched_at):
    observation_date = (
        df["Tarih"].max().strftime("%d.%m.%Y")
        if not df.empty
        else "Veri yok"
    )

    st.caption(
        f"**Son veri çekimi:** {fetched_at}  |  "
        f"**Son gözlem tarihi:** {observation_date}  |  "
        "Önbellek süresi: 1 saat | Verileri yenile düğmesiyle önbelleği temizleyebilirsiniz"
    )


def latest_value(df, column):
    if column not in df.columns or df.empty:
        return float("nan")
    return df.iloc[-1][column]


def latest_difference(df, column, periods=1):
    if column not in df.columns or len(df) <= periods:
        return float("nan")
    return df[column].iloc[-1] - df[column].iloc[-1 - periods]


def format_value(value, decimals=2):
    if pd.isna(value):
        return "Veri yok"
    return f"{value:+,.{decimals}f}"


def add_line_end_labels(fig, decimals=2):
    """Çizgi grafiklerinin son geçerli gözlem değerini çizginin sağına yazar."""
    annotations = []

    for trace in fig.data:
        if trace.type != "scatter" or trace.mode is None or "lines" not in trace.mode:
            continue

        points = [
            (x, y)
            for x, y in zip(trace.x, trace.y)
            if pd.notna(x) and pd.notna(y)
        ]

        if not points:
            continue

        last_x, last_y = points[-1]
        trace_color = getattr(trace.line, "color", None) or "#374151"

        annotations.append(
            dict(
                x=last_x,
                y=last_y,
                xref="x",
                yref="y",
                text=f"{last_y:,.{decimals}f}",
                showarrow=False,
                xanchor="left",
                yanchor="middle",
                xshift=9,
                font=dict(
                    size=12,
                    color=trace_color,
                ),
                bgcolor="rgba(255,255,255,0.88)",
                bordercolor=trace_color,
                borderwidth=1,
                borderpad=3,
            )
        )

    if annotations:
        fig.update_layout(
            annotations=list(fig.layout.annotations or ()) + annotations,
            margin=dict(
                l=60,
                r=105,
                t=75,
                b=55,
            ),
        )

    return fig


def fig_to_png(fig):
    """
    Plotly grafiğini Kaleido kullanmadan Matplotlib ile PNG'ye çevirir.
    """

    mpl_fig, ax = plt.subplots(figsize=(14, 7))

    has_data = False

    for trace in fig.data:

        x = list(trace.x) if trace.x is not None else []
        y = list(trace.y) if trace.y is not None else []

        if not x or not y:
            continue

        color = None

        if trace.type == "bar":

            ax.bar(
                x,
                y,
                label=trace.name or "Seri",
                alpha=0.8,
            )

            has_data = True

        elif trace.type == "scatter":

            mode = trace.mode or "lines"

            if "lines" in mode:
                ax.plot(
                    x,
                    y,
                    label=trace.name or "Seri",
                    linewidth=2,
                )

                valid_points = [
                    (xv, yv)
                    for xv, yv in zip(x, y)
                    if pd.notna(xv) and pd.notna(yv)
                ]

                if valid_points:
                    last_x, last_y = valid_points[-1]

                    ax.annotate(
                        f"{last_y:,.2f}",
                        xy=(last_x, last_y),
                        xytext=(8, 0),
                        textcoords="offset points",
                        fontsize=9,
                    )

                has_data = True

            elif "markers" in mode:
                ax.scatter(
                    x,
                    y,
                    label=trace.name or "Seri",
                )

                has_data = True

    title = ""

    if fig.layout.title and fig.layout.title.text:
        title = fig.layout.title.text

    x_title = ""
    y_title = ""

    if fig.layout.xaxis and fig.layout.xaxis.title:
        x_title = fig.layout.xaxis.title.text or ""

    if fig.layout.yaxis and fig.layout.yaxis.title:
        y_title = fig.layout.yaxis.title.text or ""

    ax.set_title(title, fontsize=15, fontweight="bold", pad=18)
    ax.set_xlabel(x_title)
    ax.set_ylabel(y_title)

    ax.grid(True, alpha=0.25)

    if has_data:
        ax.legend(loc="best", fontsize=9)

    # Tarih eksenini okunabilir hale getir.
    try:
        ax.xaxis.set_major_formatter(
            mdates.DateFormatter("%d.%m.%Y")
        )
        mpl_fig.autofmt_xdate()
    except Exception:
        pass

    mpl_fig.tight_layout()

    buffer = io.BytesIO()

    mpl_fig.savefig(
        buffer,
        format="png",
        dpi=180,
        bbox_inches="tight",
    )

    plt.close(mpl_fig)

    buffer.seek(0)

    return buffer.getvalue()

def send_email(subject, body, attachments):
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = GMAIL_ADDRESS
    message["To"] = EMAIL_RECIPIENT
    message.set_content(body)

    for filename, image_bytes in attachments:
        message.add_attachment(
            image_bytes,
            maintype="image",
            subtype="png",
            filename=filename,
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        smtp.send_message(message)


def show_date_filters(key_prefix):
    today = date.today()
    default_start = date(today.year, 1, 1)

    st.markdown("#### Analiz Dönemi")
    st.caption("Varsayılan dönem yılbaşından bugüne kadardır. İsterseniz tarihleri değiştirebilirsiniz.")
    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input(
            "Başlangıç tarihi",
            value=default_start,
            max_value=today,
            key=f"{key_prefix}_start",
        )

    with col2:
        end_date = st.date_input(
            "Bitiş tarihi",
            value=today,
            max_value=today,
            key=f"{key_prefix}_end",
        )

    if start_date > end_date:
        st.error("Başlangıç tarihi bitiş tarihinden sonra olamaz.")
        st.stop()

    if st.button("Verileri yenile", key=f"{key_prefix}_refresh"):
        fetch_evds_data.clear()
        st.rerun()

    return (
        start_date.strftime("%d-%m-%Y"),
        end_date.strftime("%d-%m-%Y"),
    )


# =========================================================
# PANEL SEÇİMİ
# =========================================================

panel = st.radio(
    "Analiz alanı",
    ["YP Mevduat", "TL Mevduat"],
    horizontal=True,
)


# =========================================================
# TL MEVDUAT PANELİ
# =========================================================

if panel == "TL Mevduat":

    st.header("TL Mevduat")
    st.caption("TL mevduat stokunun gelişimi, müşteri grupları ve vade kompozisyonu.")
    start_date, end_date = show_date_filters("tl")

    with st.spinner("TL mevduat verileri getiriliyor..."):
        try:
            tl_df, tl_fetched_at = fetch_evds_data(
                start_date,
                end_date,
                tuple(TL_SERIES.items()),
            )
        except Exception as e:
            st.error(f"TL verileri alınamadı: {e}")
            st.stop()

    show_data_status(tl_df, tl_fetched_at)

    available_tl_columns = [
        name for name in TL_SERIES if name in tl_df.columns
    ]

    if tl_df.empty or "Toplam TL Mevduat" not in available_tl_columns:
        st.error("Toplam TL Mevduat serisi bulunamadı.")
        st.stop()

    # Milyon TL -> trilyon TL
    tl_df[available_tl_columns] = (
        tl_df[available_tl_columns] / 1_000_000
    )

    total_col = "Toplam TL Mevduat"

    # Seviye: trilyon TL; değişim: milyar TL
    tl_df["Haftalık Değişim"] = tl_df[total_col].diff() * 1000
    tl_df["Haftalık Değişim (%)"] = tl_df[total_col].pct_change() * 100

    tl_df["4 Haftalık Değişim"] = (
        tl_df[total_col] - tl_df[total_col].shift(4)
    ) * 1000
    tl_df["4 Haftalık Değişim (%)"] = (
        tl_df[total_col].pct_change(4) * 100
    )

    tl_df["13 Haftalık Değişim"] = (
        tl_df[total_col] - tl_df[total_col].shift(13)
    ) * 1000
    tl_df["13 Haftalık Değişim (%)"] = (
        tl_df[total_col].pct_change(13) * 100
    )

    latest_tl = tl_df.iloc[-1]

    st.subheader("Öne Çıkan Göstergeler")
    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Toplam TL Mevduat",
        f"{latest_tl[total_col]:,.2f} trilyon TL",
    )

    resident = latest_value(tl_df, "Yurt İçi Yerleşikler")
    c2.metric(
        "Yurt İçi Yerleşikler",
        f"{resident:,.2f} trilyon TL" if pd.notna(resident) else "Veri yok",
    )

    weekly = latest_tl["Haftalık Değişim"]
    weekly_pct = latest_tl["Haftalık Değişim (%)"]

    c3.metric(
        "Haftalık Değişim",
        f"{weekly:+,.1f} milyar TL" if pd.notna(weekly) else "Veri yok",
        f"{weekly_pct:+.2f}%" if pd.notna(weekly_pct) else None,
    )

    four_week = latest_tl["4 Haftalık Değişim"]
    four_pct = latest_tl["4 Haftalık Değişim (%)"]

    c4.metric(
        "4 Haftalık Değişim",
        f"{four_week:+,.1f} milyar TL" if pd.notna(four_week) else "Veri yok",
        f"{four_pct:+.2f}%" if pd.notna(four_pct) else None,
    )

    st.caption(
        "Mevduat stokları trilyon TL, değişim tutarları milyar TL cinsindendir."
    )

    fig_total = px.line(
        tl_df,
        x="Tarih",
        y=total_col,
        title="Toplam TL Mevduat",
        labels={"Tarih": "Tarih", total_col: "Trilyon TL"},
    )
    fig_total.update_yaxes(title_text="Trilyon TL")
    fig_total.update_layout(hovermode="x unified")
    st.plotly_chart(fig_total, use_container_width=True)

    person_columns = [
        "Gerçek Kişiler",
        "Ticari Kuruluşlar",
        "Resmî Kuruluşlar",
        "Kâr Amacı Olmayan Kuruluşlar",
        "Banka Dışı Finansal Kuruluşlar",
    ]
    person_columns = [c for c in person_columns if c in tl_df.columns]
    fig_person = None

    if person_columns:
        person_long = tl_df[["Tarih"] + person_columns].melt(
            id_vars="Tarih",
            var_name="Mevduat Türü",
            value_name="Tutar",
        )

        fig_person = px.line(
            person_long,
            x="Tarih",
            y="Tutar",
            color="Mevduat Türü",
            title="Mevduat Türlerine Göre Gelişim",
            labels={"Tarih": "Tarih", "Tutar": "Trilyon TL"},
        )
        fig_person.update_yaxes(title_text="Trilyon TL")
        fig_person.update_layout(hovermode="x unified")
        st.plotly_chart(fig_person, use_container_width=True)

    maturity_columns = [
        "Gerçek Kişiler - Vadesiz",
        "Gerçek Kişiler - Vadeli",
        "Ticari Kuruluşlar - Vadesiz",
        "Ticari Kuruluşlar - Vadeli",
        "Resmî Kuruluşlar - Vadesiz",
        "Resmî Kuruluşlar - Vadeli",
        "Kâr Amacı Olmayan Kuruluşlar - Vadesiz",
        "Kâr Amacı Olmayan Kuruluşlar - Vadeli",
        "Banka Dışı Finansal Kuruluşlar - Vadesiz",
        "Banka Dışı Finansal Kuruluşlar - Vadeli",
    ]
    maturity_columns = [c for c in maturity_columns if c in tl_df.columns]
    fig_maturity = None

    if maturity_columns:
        maturity_long = tl_df[["Tarih"] + maturity_columns].melt(
            id_vars="Tarih",
            var_name="Mevduat Türü",
            value_name="Tutar",
        )

        fig_maturity = px.line(
            maturity_long,
            x="Tarih",
            y="Tutar",
            color="Mevduat Türü",
            title="Vadeli / Vadesiz Mevduat",
            labels={"Tarih": "Tarih", "Tutar": "Trilyon TL"},
        )
        fig_maturity.update_yaxes(title_text="Trilyon TL")
        fig_maturity.update_layout(hovermode="x unified")
        st.plotly_chart(fig_maturity, use_container_width=True)

    fig_weekly = px.bar(
        tl_df,
        x="Tarih",
        y="Haftalık Değişim",
        title="Toplam TL Mevduatta Haftalık Değişim",
        labels={"Tarih": "Tarih", "Haftalık Değişim": "Milyar TL"},
    )
    fig_weekly.update_yaxes(title_text="Milyar TL")
    st.plotly_chart(fig_weekly, use_container_width=True)

    st.subheader("Haftalık Görünüm")

    weekly_table = tl_df[
        ["Tarih", total_col, "Haftalık Değişim", "Haftalık Değişim (%)"]
    ].copy().rename(columns={
        total_col: "Toplam TL Mevduat (Trilyon TL)",
        "Haftalık Değişim": "Haftalık Değişim (Milyar TL)",
    })

    st.dataframe(
        weekly_table.sort_values("Tarih", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Son 4 Haftalık Değişim")

    four_table = tl_df[
        ["Tarih", total_col, "4 Haftalık Değişim", "4 Haftalık Değişim (%)"]
    ].copy().rename(columns={
        total_col: "Toplam TL Mevduat (Trilyon TL)",
        "4 Haftalık Değişim": "4 Haftalık Değişim (Milyar TL)",
    })

    st.dataframe(
        four_table.sort_values("Tarih", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Son 13 Haftalık Değişim")

    thirteen_table = tl_df[
        ["Tarih", total_col, "13 Haftalık Değişim", "13 Haftalık Değişim (%)"]
    ].copy().rename(columns={
        total_col: "Toplam TL Mevduat (Trilyon TL)",
        "13 Haftalık Değişim": "13 Haftalık Değişim (Milyar TL)",
    })

    st.dataframe(
        thirteen_table.sort_values("Tarih", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Veriyi Dışa Aktar")

    csv_df = tl_df.copy()
    csv_rename = {
        name: f"{name} (Trilyon TL)"
        for name in TL_SERIES
        if name in csv_df.columns
    }
    csv_rename.update({
        "Haftalık Değişim": "Haftalık Değişim (Milyar TL)",
        "4 Haftalık Değişim": "4 Haftalık Değişim (Milyar TL)",
        "13 Haftalık Değişim": "13 Haftalık Değişim (Milyar TL)",
    })
    csv_df = csv_df.rename(columns=csv_rename)

    st.download_button(
        "TL Mevduat Verisini İndir (CSV)",
        data=csv_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="tl_mevduat_analiz.csv",
        mime="text/csv",
    )

    st.subheader("E-posta Raporu")

    if st.button("TL Mevduat Raporunu Gönder"):
        try:
            attachments = [
                ("toplam_tl_mevduat.png", fig_to_png(fig_total)),
                ("haftalik_degisim.png", fig_to_png(fig_weekly)),
            ]

            if fig_person is not None:
                attachments.append(
                    ("mevduat_turleri.png", fig_to_png(fig_person))
                )

            if fig_maturity is not None:
                attachments.append(
                    ("vadeli_vadesiz.png", fig_to_png(fig_maturity))
                )

            send_email(
                "TL Mevduat | Haftalık Analiz",
                "TL mevduat analiz raporunuz ekte yer almaktadır.",
                attachments,
            )
            st.success("E-posta başarıyla gönderildi.")

        except Exception as e:
            st.error(f"E-posta gönderilemedi: {e}")

    st.stop()


# =========================================================
# YP MEVDUAT PANELİ — YENİ TASARIM
# =========================================================

import plotly.graph_objects as go

st.header("Yabancı Para Mevduatları")
st.caption("Gerçek ve tüzel kişiler, varlık kırılımları ve haftalık parite bileşenleri.")
start_date, end_date = show_date_filters("yp")

all_yp_series = {**YP_LEVEL_SERIES, **YP_CHANGE_SERIES}
with st.spinner("YP DTH verileri getiriliyor..."):
    try:
        yp_df, yp_fetched_at = fetch_evds_data(
            start_date, end_date, tuple(all_yp_series.items())
        )
    except Exception as exc:
        st.error(f"YP verileri alınamadı: {exc}")
        st.stop()

show_data_status(yp_df, yp_fetched_at)
if yp_df.empty:
    st.warning("Seçilen dönemde veri bulunamadı.")
    st.stop()

yp_df = yp_df.sort_values("Tarih").reset_index(drop=True)
required = ["Gerçek Kişiler", "Tüzel Kişiler"]
missing = [name for name in required if name not in yp_df.columns]
if missing:
    st.error("EVDS yanıtında gerekli seriler yok: " + ", ".join(missing))
    st.stop()

latest_date = yp_df["Tarih"].max()
SEGMENTS = {"Gerçek Kişiler": "#247BA0", "Tüzel Kişiler": "#F28E2B"}
CHANGE_COLORS = {
    "Nominal": "#64748B",
    "Parite Hariç": "#16A34A",
    "Parite Etkisi": "#8B5CF6",
}


def fmt(value, digits=2):
    return "Veri yok" if pd.isna(value) else f"{value:+,.{digits}f}"


def last_valid(series):
    values = pd.to_numeric(series, errors="coerce").dropna()
    return values.iloc[-1] if not values.empty else float("nan")


def style_chart(fig, unit="EVDS seri birimi", zero=False):
    fig.update_layout(
        template="plotly_white", hovermode="x unified", height=400,
        margin=dict(l=35, r=115, t=60, b=45),
        legend_title_text="", legend=dict(orientation="h", y=1.13, x=0),
        xaxis_title=None, yaxis_title=unit,
        font=dict(size=12),
    )
    fig.update_xaxes(tickformat="%d.%m.%y", showgrid=False)
    fig.update_yaxes(tickformat=",.2f", zeroline=zero, separatethousands=True)
    return fig


def plot_lines(data, columns, title, unit="EVDS seri birimi", colors=None):
    fig = go.Figure()
    for label, col in columns.items():
        if col not in data:
            continue
        valid = data[["Tarih", col]].dropna()
        if valid.empty:
            continue
        color = (colors or SEGMENTS).get(label, "#475569")
        fig.add_trace(go.Scatter(
            x=valid["Tarih"], y=valid[col], name=label,
            mode="lines", line=dict(width=2.8, color=color),
        ))
        x, y = valid.iloc[-1]["Tarih"], valid.iloc[-1][col]
        fig.add_annotation(
            x=x, y=y, text=f"{y:+,.2f}", showarrow=False,
            xanchor="left", xshift=10, font=dict(color=color, size=11),
            bgcolor="rgba(255,255,255,.9)", bordercolor=color, borderwidth=1,
        )
    fig.update_layout(title=title)
    return style_chart(fig, unit)


def plot_weekly_bars(data, columns, title, unit="EVDS seri birimi", colors=None):
    fig = go.Figure()
    for label, col in columns.items():
        if col not in data:
            continue
        valid = data[["Tarih", col]].dropna()
        if valid.empty:
            continue
        color = (colors or SEGMENTS).get(label, "#475569")
        fig.add_trace(go.Bar(
            x=valid["Tarih"], y=valid[col], name=label,
            marker_color=color,
            customdata=[f"{v:+,.2f}" for v in valid[col]],
            hovertemplate="%{x|%d.%m.%Y}<br>%{customdata}<extra>%{fullData.name}</extra>",
        ))
        x, y = valid.iloc[-1]["Tarih"], valid.iloc[-1][col]
        fig.add_annotation(
            x=x, y=y, text=f"{y:+,.2f}", showarrow=True,
            arrowhead=0, ax=40, ay=(-30 if y >= 0 else 30),
            font=dict(color=color, size=11),
            bgcolor="rgba(255,255,255,.95)", bordercolor=color, borderwidth=1,
        )
    fig.update_layout(title=title, barmode="group")
    return style_chart(fig, unit, zero=True)


st.subheader(f"Müşteri Grupları | {latest_date:%d.%m.%Y}")
c1, c2 = st.columns(2)
for widget, segment in zip((c1, c2), SEGMENTS):
    value = last_valid(yp_df[segment])
    diff = yp_df[segment].diff().dropna()
    delta = diff.iloc[-1] if not diff.empty else float("nan")
    widget.metric(
        segment, f"{value:,.2f}" if pd.notna(value) else "Veri yok",
        delta=f"{delta:+,.2f} (haftalık)" if pd.notna(delta) else None,
    )
st.caption("Seviye ve haftalık değişim tutarları EVDS kaynak serilerinin birimindedir; toplam YP mevduat bu kartlarda gösterilmez.")

st.subheader("Haftalık Parite Etkisinden Arındırılmış Değişim")
parity_main = {
    "Gerçek Kişiler": "Parite Hariç - Gerçek Kişiler",
    "Tüzel Kişiler": "Parite Hariç - Tüzel Kişiler",
}
p1, p2 = st.columns(2)
for widget, (segment, col) in zip((p1, p2), parity_main.items()):
    widget.metric(segment, fmt(last_valid(yp_df[col])) if col in yp_df else "Veri yok")
st.caption("Bu göstergeler TCMB'nin haftalık parite etkisinden arındırılmış değişim serileridir; stok farkından hesaplanmaz.")

st.subheader("Mevduat Seviyeleri ve Nominal Değişim")
fig_main = plot_lines(yp_df, {s: s for s in SEGMENTS}, "Gerçek ve Tüzel Kişi Mevduat Seviyeleri")
st.plotly_chart(fig_main, use_container_width=True)
nominal_main = yp_df[["Tarih"] + list(SEGMENTS)].copy()
for segment in SEGMENTS:
    nominal_main[segment] = nominal_main[segment].diff()
fig_nominal = plot_weekly_bars(
    nominal_main, {s: s for s in SEGMENTS}, "Haftalık Nominal Değişim"
)
st.plotly_chart(fig_nominal, use_container_width=True)
fig_adjusted = plot_weekly_bars(
    yp_df, parity_main, "Haftalık Parite Hariç Değişim"
)
st.plotly_chart(fig_adjusted, use_container_width=True)
fig_parity = plot_weekly_bars(
    yp_df,
    {s: f"Parite Etkisi - {s}" for s in SEGMENTS},
    "Haftalık Parite Etkisi",
)
st.plotly_chart(fig_parity, use_container_width=True)

BREAKDOWN = {
    "USD": ("USD", "USD"),
    "EUR": ("EUR", "EUR"),
    "Diğer Döviz": ("Diğer Döviz", "Diğer Döviz"),
    "Altın": ("Altın", "Altın"),
}

st.subheader("Varlık Türüne Göre Analiz")
st.caption("Her varlık için seviyeler, haftalık nominal değişim, parite hariç değişim ve parite etkisi ayrı ayrı gösterilir. Sağdaki etiketler son geçerli gözleme aittir.")
summary_rows = []
email_figures = [("ana_seviye", fig_main), ("ana_nominal", fig_nominal),
                 ("ana_parite_haric", fig_adjusted), ("ana_parite_etkisi", fig_parity)]

for asset in BREAKDOWN:
    with st.expander(f"{asset} | Ayrıntılı Grafikler", expanded=(asset == "USD")):
        level_cols = {s: f"{s} - {asset}" for s in SEGMENTS}
        adjusted_cols = {s: f"Parite Hariç - {s} {asset}" for s in SEGMENTS}
        parity_cols = {s: f"Parite Etkisi - {s} {asset}" for s in SEGMENTS}
        nominal_df = yp_df[["Tarih"]].copy()
        for segment, level_col in level_cols.items():
            if level_col in yp_df:
                nominal_df[segment] = yp_df[level_col].diff()
        charts = [
            ("seviye", plot_lines(yp_df, level_cols, f"{asset} — Mevduat Seviyeleri")),
            ("nominal", plot_weekly_bars(nominal_df, {s: s for s in SEGMENTS}, f"{asset} — Haftalık Nominal Değişim")),
            ("parite_haric", plot_weekly_bars(yp_df, adjusted_cols, f"{asset} — Parite Hariç Değişim")),
            ("parite_etkisi", plot_weekly_bars(yp_df, parity_cols, f"{asset} — Parite Etkisi")),
        ]
        for kind, fig in charts:
            st.plotly_chart(fig, use_container_width=True)
            email_figures.append((f"{asset.lower().replace(' ', '_')}_{kind}", fig))
        for segment in SEGMENTS:
            lc, ac, pc = level_cols[segment], adjusted_cols[segment], parity_cols[segment]
            summary_rows.append({
                "Varlık": asset, "Grup": segment,
                "Seviye": last_valid(yp_df[lc]) if lc in yp_df else float("nan"),
                "Nominal": last_valid(nominal_df[segment]) if segment in nominal_df else float("nan"),
                "Parite Hariç": last_valid(yp_df[ac]) if ac in yp_df else float("nan"),
                "Parite Etkisi": last_valid(yp_df[pc]) if pc in yp_df else float("nan"),
            })

st.subheader("Yılbaşından Bugüne | Birikimli Parite Hariç Değişim")
selected_start = pd.to_datetime(start_date, format="%d-%m-%Y")
year_start = pd.Timestamp(latest_date.year, 1, 1)
if selected_start > year_start:
    st.info("YTD hesaplaması için yılbaşından itibaren veri gerekir. Seçili tarih aralığı yılbaşından sonra başladığı için YTD bölümü gösterilmiyor. Başlangıç tarihini 1 Ocak'a alın.")
else:
    ytd_data = yp_df[(yp_df["Tarih"] >= year_start) & (yp_df["Tarih"] <= latest_date)]
    ytd_rows = []
    ytd_fig = go.Figure()
    for segment in SEGMENTS:
        for asset in ("USD", "EUR", "Altın"):
            col = f"Parite Hariç - {segment} {asset}"
            if col not in ytd_data:
                continue
            valid = ytd_data[["Tarih", col]].dropna()
            if valid.empty:
                continue
            cumulative = valid[col].cumsum()
            total = cumulative.iloc[-1]
            ytd_rows.append({"Grup": segment, "Varlık": asset,
                             "Birikimli Parite Hariç Değişim": total,
                             "Gözlem Sayısı": len(valid)})
            ytd_fig.add_trace(go.Scatter(
                x=valid["Tarih"], y=cumulative,
                mode="lines", name=f"{segment} | {asset}",
            ))
    if ytd_rows:
        ytd_fig.update_layout(title=f"{latest_date.year} YTD — Kümülatif Parite Hariç Değişim")
        st.plotly_chart(style_chart(ytd_fig), use_container_width=True)
        st.dataframe(pd.DataFrame(ytd_rows), use_container_width=True, hide_index=True)
        email_figures.append(("ytd_birikimli_parite_haric", ytd_fig))
        st.caption("YTD değerleri, yılbaşından son yayımlanan gözleme kadar EVDS haftalık parite hariç değişimlerinin toplamıdır. USD/EUR/altın başlıkları varlık kırılımını belirtir; birimler EVDS seri tanımından teyit edilmeden farklı varlıkların tutarları birbirine eklenmemelidir. Eksik haftalar varsa kümülatif toplam yalnızca mevcut gözlemleri kapsar.")
    else:
        st.warning("YTD hesaplaması için gerekli haftalık seriler bulunamadı.")

st.subheader("Son Haftanın Sayısal Özeti")
st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
st.caption("Nominal = stok serisinin haftalık farkı. Parite Hariç ve Parite Etkisi = TCMB'nin ayrı haftalık EVDS serileri. Bu sütunlar otomatik olarak birbirine eşit kabul edilmez.")

st.subheader("Detaylı Veri ve CSV")
st.dataframe(yp_df.sort_values("Tarih", ascending=False), use_container_width=True, hide_index=True)
st.download_button(
    "YP verisini CSV indir", data=yp_df.to_csv(index=False).encode("utf-8-sig"),
    file_name="yp_mevduat_analiz.csv", mime="text/csv",
)

st.subheader("E-posta Raporu")
st.caption("Grafikler PNG formatında hazırlanır; Kaleido gerektirmez.")
if st.button("YP Raporunu E-posta ile Gönder"):
    try:
        attachments = [(f"{name}.png", fig_to_png(fig)) for name, fig in email_figures]
        send_email(
            "YP Mevduat | Haftalık Analiz",
            f"YP mevduat analiz raporu. Son gözlem: {latest_date:%d.%m.%Y}.\n"
            "Nominal, parite hariç ve parite etkisi ayrı grafiklerde; YTD kümülatif analiz ektedir.",
            attachments,
        )
        st.success("Rapor e-posta ile gönderildi.")
    except Exception as exc:
        st.error(f"E-posta gönderilemedi: {exc}")

