import smtplib
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
from html import escape
from urllib.parse import urlparse

from email.message import EmailMessage
from email.utils import make_msgid
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

# Dashboard bağlantısı doğrudan tanımlıdır; Secrets ayarı gerekmez.
DASHBOARD_URL = "https://tcmb-fx-dashboard-8uo7dmttxrsgsnrh47ydxh.streamlit.app/"
if DASHBOARD_URL:
    parsed_dashboard_url = urlparse(DASHBOARD_URL)
    if parsed_dashboard_url.scheme != "https" or not parsed_dashboard_url.netloc:
        DASHBOARD_URL = ""

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

            bars = ax.bar(
                x,
                y,
                label=trace.name or "Seri",
                alpha=0.8,
                width=2.2 if len(x) > 1 else 0.6,
            )
            # Son haftanın tutarını her seri için çubuk üzerinde göster.
            valid_indices = [i for i, v in enumerate(y) if pd.notna(v)]
            if valid_indices:
                idx = valid_indices[-1]
                last_bar = bars[idx]
                last_y = float(y[idx])
                ax.annotate(
                    f"{last_y:+,.2f}",
                    xy=(last_bar.get_x() + last_bar.get_width() / 2, last_y),
                    xytext=(0, -13 if last_y < 0 else 7),
                    textcoords="offset points", ha="center",
                    va="top" if last_y < 0 else "bottom",
                    fontsize=9, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9),
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

def send_email(subject, body, attachments, html_body=None, inline_images=None):
    """HTML görsellerini CID ile göm; PNG eklerini ayrıca sakla."""
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = GMAIL_ADDRESS
    message["To"] = EMAIL_RECIPIENT
    message.set_content(body)
    if html_body:
        cid_map = {}
        for label, _ in (inline_images or []):
            cid_map[label] = make_msgid(domain="mevduat-raporu.local")
        for label, cid in cid_map.items():
            html_body = html_body.replace("{" + label + "}", cid[1:-1])
        message.add_alternative(html_body, subtype="html")
        html_part = message.get_payload()[-1]
        for label, image_bytes in (inline_images or []):
            html_part.add_related(
                image_bytes, maintype="image", subtype="png",
                cid=cid_map[label], filename=f"{label}.png",
                disposition="inline",
            )
    for filename, image_bytes in attachments:
        message.add_attachment(
            image_bytes, maintype="image", subtype="png", filename=filename,
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
    import plotly.graph_objects as go

    st.header("TL Mevduat")
    st.caption("Mevduat stoku, müşteri grupları ve vadeli/vadesiz kompozisyonu.")
    st.info("📅 **Analiz tarihlerini değiştirebilirsiniz.** Aşağıdaki başlangıç ve bitiş tarihlerini seçerek grafikleri ve tabloları istediğiniz dönem için güncelleyebilirsiniz.")
    start_date, end_date = show_date_filters("tl")

    with st.spinner("TL mevduat verileri getiriliyor..."):
        try:
            tl_df, tl_fetched_at = fetch_evds_data(
                start_date, end_date, tuple(TL_SERIES.items())
            )
        except Exception as e:
            st.error(f"TL verileri alınamadı: {e}")
            st.stop()

    show_data_status(tl_df, tl_fetched_at)
    if tl_df.empty or "Toplam TL Mevduat" not in tl_df.columns:
        st.error("Toplam TL Mevduat serisi bulunamadı.")
        st.stop()

    # EVDS kaynak serileri milyon TL: stokları trilyon, değişimleri milyar TL gösteriyoruz.
    tl_cols = [c for c in TL_SERIES if c in tl_df.columns]
    tl_df[tl_cols] = tl_df[tl_cols].apply(pd.to_numeric, errors="coerce") / 1_000_000
    tl_df = tl_df.sort_values("Tarih").reset_index(drop=True)
    total_col = "Toplam TL Mevduat"
    tl_df["Haftalık Değişim"] = tl_df[total_col].diff() * 1000
    tl_df["Haftalık Değişim (%)"] = tl_df[total_col].pct_change(fill_method=None) * 100
    for n, label in [(4, "4 Haftalık"), (13, "13 Haftalık")]:
        tl_df[f"{label} Değişim"] = (tl_df[total_col] - tl_df[total_col].shift(n)) * 1000
        tl_df[f"{label} Değişim (%)"] = tl_df[total_col].pct_change(n, fill_method=None) * 100

    def tl_number(value, decimals=2, signed=False):
        if pd.isna(value):
            return "—"
        return f"{value:{'+' if signed else ''},.{decimals}f}"

    def tl_plot(title, columns, unit="Trilyon TL", change=False):
        fig = go.Figure()
        palette = ["#2563eb", "#0f766e", "#ea580c", "#9333ea", "#64748b"]
        annotations = []
        for i, name in enumerate(columns):
            if name not in tl_df.columns:
                continue
            subset = tl_df[["Tarih", name]].dropna()
            if subset.empty:
                continue
            values = subset[name]
            color = palette[i % len(palette)]
            fig.add_trace(go.Scatter(
                x=subset["Tarih"], y=values, name=name, mode="lines",
                line=dict(color=color, width=2.7)
            ))
            annotations.append((subset["Tarih"].iloc[-1], values.iloc[-1], color))
        for x, y, color in annotations:
            fig.add_annotation(
                x=x, y=y, xref="x", yref="y",
                text=tl_number(y, 2 if not change else 1, signed=change),
                showarrow=False, xanchor="left", xshift=12,
                font=dict(size=11, color=color),
                bgcolor="rgba(255,255,255,.95)",
                bordercolor=color, borderwidth=1
            )
        fig.update_layout(
            title=None, template="plotly_white", height=430,
            margin=dict(l=65, r=160, t=75, b=65),
            legend=dict(orientation="h", y=1.15, yanchor="bottom",
                        x=0, xanchor="left", title_text=""),
            hovermode="x unified",
            xaxis_title="Tarih", yaxis_title=unit,
            font=dict(size=12)
        )
        fig.update_xaxes(tickformat="%d.%m.%y", showgrid=False)
        fig.update_yaxes(tickformat=",.2f", separatethousands=True)
        return fig

    def tl_change_table(columns):
        records = []
        for name in columns:
            if name not in tl_df.columns:
                continue
            valid = tl_df[name].dropna()
            if valid.empty:
                continue
            last = valid.iloc[-1]
            weekly = (valid.iloc[-1] - valid.iloc[-2]) * 1000 if len(valid) > 1 else float("nan")
            records.append({
                "Mevduat Türü": name,
                "Güncel Stok (Trilyon TL)": tl_number(last),
                "Haftalık Değişim (Milyar TL)": tl_number(weekly, 1, signed=True),
            })
        return pd.DataFrame(records)

    latest = tl_df.iloc[-1]
    st.subheader("TL Mevduat Görünümü")
    # Dört kartta da aynı punto; rakamlar tam sayıya yuvarlanır.
    # Birim ayrı satırda gösterilerek rakamların sıkışması engellenir.
    st.markdown("""
    <style>
      .tl-kpi-card {
        border: 1px solid rgba(128,128,128,.22);
        border-radius: 10px;
        padding: 12px 10px;
        min-height: 124px;
        text-align: center;
        box-sizing: border-box;
      }
      .tl-kpi-title {font-size: 12px; line-height: 1.3; min-height: 32px; color: #64748b; font-weight: 600;}
      .tl-kpi-number {font-size: 21px; line-height: 1.3; font-weight: 700; white-space: nowrap; font-variant-numeric: tabular-nums;}
      .tl-kpi-unit {font-size: 12px; line-height: 1.5; color: #64748b;}
      .tl-kpi-delta {font-size: 12px; line-height: 1.5; font-weight: 600;}
      @media(max-width: 1100px) { .tl-kpi-number {font-size: 18px;} }
    </style>
    """, unsafe_allow_html=True)

    def tl_kpi(title, number, unit, delta=None, positive=None):
        from html import escape as html_escape
        color = ("#15803d" if positive else "#dc2626") if positive is not None else "#64748b"
        delta_html = (f'<div class="tl-kpi-delta" style="color:{color}">{html_escape(delta)}</div>'
                      if delta else '<div class="tl-kpi-delta">&nbsp;</div>')
        st.markdown(
            f'<div class="tl-kpi-card">'
            f'<div class="tl-kpi-title">{html_escape(title)}</div>'
            f'<div class="tl-kpi-number">{html_escape(number)}</div>'
            f'<div class="tl-kpi-unit">{html_escape(unit)}</div>'
            f'{delta_html}</div>', unsafe_allow_html=True
        )

    resident = latest_value(tl_df, "Yurt İçi Yerleşikler")
    w, wp = latest["Haftalık Değişim"], latest["Haftalık Değişim (%)"]
    a4, p4 = latest["4 Haftalık Değişim"], latest["4 Haftalık Değişim (%)"]
    kpi_cols = st.columns(4, gap="small")
    with kpi_cols[0]:
        tl_kpi("Toplam TL Mevduat", tl_number(latest[total_col], 0), "Trilyon TL")
    with kpi_cols[1]:
        tl_kpi("Yurt İçi Yerleşikler", tl_number(resident, 0), "Trilyon TL")
    with kpi_cols[2]:
        tl_kpi("Haftalık Değişim", tl_number(w, 0, True), "Milyar TL",
               f"{tl_number(wp, 0, True)}%" if pd.notna(wp) else None,
               bool(w >= 0) if pd.notna(w) else None)
    with kpi_cols[3]:
        tl_kpi("4 Haftalık Değişim", tl_number(a4, 0, True), "Milyar TL",
               f"{tl_number(p4, 0, True)}%" if pd.notna(p4) else None,
               bool(a4 >= 0) if pd.notna(a4) else None)
    st.caption("Stoklar trilyon TL, değişimler milyar TL cinsindedir. Kartlardaki değerler tam sayıya yuvarlanmıştır.")

    st.subheader("Toplam TL Mevduat")
    fig_total = tl_plot("Toplam TL Mevduat", [total_col])
    st.plotly_chart(fig_total, use_container_width=True)

    st.subheader("Toplam TL Mevduatta Haftalık Değişim")
    fig_weekly = go.Figure()
    weekly_valid = tl_df[["Tarih", "Haftalık Değişim"]].dropna()
    fig_weekly.add_trace(go.Bar(
        x=weekly_valid["Tarih"], y=weekly_valid["Haftalık Değişim"],
        name="Haftalık Değişim",
        marker_color=["#15803d" if v >= 0 else "#dc2626"
                      for v in weekly_valid["Haftalık Değişim"]]
    ))
    if not weekly_valid.empty:
        lx, ly = weekly_valid.iloc[-1][["Tarih", "Haftalık Değişim"]]
        fig_weekly.add_annotation(
            x=lx, y=ly, text=f"{tl_number(ly, 1, True)} milyar TL",
            showarrow=True, arrowhead=2, ay=-35 if ly >= 0 else 35,
            font=dict(color="#15803d" if ly >= 0 else "#dc2626", size=12),
            bgcolor="white"
        )
    fig_weekly.update_layout(
        template="plotly_white", height=410, showlegend=False,
        margin=dict(l=65, r=90, t=35, b=65),
        xaxis_title="Tarih", yaxis_title="Milyar TL",
        hovermode="x unified"
    )
    fig_weekly.update_xaxes(tickformat="%d.%m.%y", showgrid=False)
    st.plotly_chart(fig_weekly, use_container_width=True)

    person_columns = [
        "Gerçek Kişiler", "Ticari Kuruluşlar", "Resmî Kuruluşlar",
        "Kâr Amacı Olmayan Kuruluşlar", "Banka Dışı Finansal Kuruluşlar"
    ]
    person_columns = [c for c in person_columns if c in tl_df.columns]
    fig_person = None
    if person_columns:
        st.subheader("Mevduat Türlerine Göre Gelişim")
        st.caption("Grafikteki son değerler güncel stokları; tablodaki +/− işaretleri haftalık değişimin yönünü gösterir.")
        fig_person = tl_plot("Mevduat Türlerine Göre Gelişim", person_columns)
        st.plotly_chart(fig_person, use_container_width=True)
        st.dataframe(tl_change_table(person_columns), use_container_width=True, hide_index=True)

    maturity_groups = {
        "Gerçek Kişiler": ["Gerçek Kişiler - Vadeli", "Gerçek Kişiler - Vadesiz"],
        "Ticari Kuruluşlar": ["Ticari Kuruluşlar - Vadeli", "Ticari Kuruluşlar - Vadesiz"],
        "Resmî Kuruluşlar": ["Resmî Kuruluşlar - Vadeli", "Resmî Kuruluşlar - Vadesiz"],
        "Kâr Amacı Olmayan Kuruluşlar": [
            "Kâr Amacı Olmayan Kuruluşlar - Vadeli",
            "Kâr Amacı Olmayan Kuruluşlar - Vadesiz"
        ],
        "Banka Dışı Finansal Kuruluşlar": [
            "Banka Dışı Finansal Kuruluşlar - Vadeli",
            "Banka Dışı Finansal Kuruluşlar - Vadesiz"
        ],
    }
    st.subheader("Vadeli / Vadesiz Mevduat")
    st.markdown("**Müşteri grubunu seçerek vadeli ve vadesiz mevduat gelişimini inceleyebilirsiniz.**")
    group = st.selectbox("Müşteri grubu", list(maturity_groups), key="tl_maturity_group")
    maturity_columns = [c for c in maturity_groups[group] if c in tl_df.columns]
    fig_maturity = None
    if maturity_columns:
        fig_maturity = tl_plot("Vadeli / Vadesiz Mevduat", maturity_columns)
        st.plotly_chart(fig_maturity, use_container_width=True)
        st.dataframe(tl_change_table(maturity_columns), use_container_width=True, hide_index=True)
    else:
        st.warning("Seçilen müşteri grubu için vade kırılımı bulunamadı.")

    st.subheader("Dönemsel Değişimler")
    tab_week, tab_four, tab_thirteen = st.tabs(["Haftalık", "Son 4 Hafta", "Son 13 Hafta"])
    for tab, period in [
        (tab_week, "Haftalık"), (tab_four, "4 Haftalık"), (tab_thirteen, "13 Haftalık")
    ]:
        with tab:
            columns = ["Tarih", total_col, f"{period} Değişim", f"{period} Değişim (%)"]
            view = tl_df[columns].copy().sort_values("Tarih", ascending=False)
            view = view.rename(columns={
                total_col: "Stok (Trilyon TL)",
                f"{period} Değişim": "Değişim (Milyar TL)",
                f"{period} Değişim (%)": "Değişim (%)"
            })
            view["Stok (Trilyon TL)"] = view["Stok (Trilyon TL)"].map(lambda x: tl_number(x, 2))
            view["Değişim (Milyar TL)"] = view["Değişim (Milyar TL)"].map(lambda x: tl_number(x, 1, True))
            view["Değişim (%)"] = view["Değişim (%)"].map(lambda x: tl_number(x, 2, True))
            st.dataframe(view, use_container_width=True, hide_index=True)

    st.subheader("Veriyi Dışa Aktar")
    csv_df = tl_df.rename(columns={
        **{c: f"{c} (Trilyon TL)" for c in tl_cols},
        "Haftalık Değişim": "Haftalık Değişim (Milyar TL)",
        "4 Haftalık Değişim": "4 Haftalık Değişim (Milyar TL)",
        "13 Haftalık Değişim": "13 Haftalık Değişim (Milyar TL)"
    })
    st.download_button(
        "TL Mevduat Verisini İndir (CSV)",
        data=csv_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="tl_mevduat_analiz.csv", mime="text/csv"
    )

    st.subheader("E-posta Raporu")
    if st.button("E-posta Gönder", key="tl_send_email"):
        try:
            attachments = [
                ("toplam_tl_mevduat.png", fig_to_png(fig_total)),
                ("haftalik_degisim.png", fig_to_png(fig_weekly)),
            ]
            if fig_person is not None:
                attachments.append(("mevduat_turleri.png", fig_to_png(fig_person)))
            if fig_maturity is not None:
                attachments.append(("vadeli_vadesiz.png", fig_to_png(fig_maturity)))
            send_email(
                "TL Mevduat | Haftalık Analiz",
                "Merhaba,\n\nTL mevduat analiz grafikleri ekte yer almaktadır.\n\nSaygılarımla,",
                attachments
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
st.info("📅 **Analiz tarihlerini değiştirebilirsiniz.** Aşağıdaki başlangıç ve bitiş tarihlerini seçerek grafikleri ve tabloları istediğiniz dönem için güncelleyebilirsiniz.")
start_date, end_date = show_date_filters("yp")

all_yp_series = {
    name: code
    for name, code in {**YP_LEVEL_SERIES, **YP_CHANGE_SERIES}.items()
    if "Diğer Döviz" not in name
}
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


# EVDS YP DTH stok ve değişim serileri milyon USD karşılığı olarak sunulur.
# Görsel ve tablo için 1.000'e bölerek milyar USD karşılığına çeviriyoruz.
YP_SCALE = 1000.0
YP_UNIT = "Milyar USD karşılığı"


def display_number(value, digits=2, signed=True):
    if pd.isna(value):
        return "Veri yok"
    sign = "+" if signed else ""
    return f"{value:{sign},.{digits}f}"


def style_chart(fig, unit=YP_UNIT, zero=False):
    # Başlık, yatay lejant ve grafik alanı arasında ayrı boşluklar.
    fig.update_layout(
        template="plotly_white", hovermode="x unified", height=440,
        margin=dict(l=65, r=150, t=115, b=55),
        title=dict(x=0.015, y=0.97, xanchor="left", yanchor="top", font=dict(size=17)),
        legend_title_text="", legend=dict(
            orientation="h", y=1.075, yanchor="bottom", x=0, xanchor="left",
            bgcolor="rgba(255,255,255,0.9)"),
        xaxis_title=None, yaxis_title=unit,
        font=dict(size=12),
        bargap=0.24,
    )
    fig.update_xaxes(tickformat="%d.%m.%y", showgrid=False)
    fig.update_yaxes(tickformat=",.2f", zeroline=zero, separatethousands=True)
    return fig


def plot_lines(data, columns, title, unit=YP_UNIT, colors=None):
    fig = go.Figure()
    for label, col in columns.items():
        if col not in data:
            continue
        valid = data[["Tarih", col]].dropna()
        if valid.empty:
            continue
        color = (colors or SEGMENTS).get(label, "#475569")
        values = valid[col] / YP_SCALE
        fig.add_trace(go.Scatter(
            x=valid["Tarih"], y=values, name=label,
            mode="lines", line=dict(width=2.8, color=color),
        ))
        x, y = valid.iloc[-1]["Tarih"], values.iloc[-1]
        fig.add_annotation(
            x=x, y=y, text=display_number(y), showarrow=False,
            xanchor="left", xshift=12, font=dict(color=color, size=11),
            bgcolor="rgba(255,255,255,.95)", bordercolor=color, borderwidth=1,
        )
    fig.update_layout(title=title)
    return style_chart(fig, unit)


def plot_weekly_bars(data, columns, title, unit=YP_UNIT, colors=None):
    fig = go.Figure()
    for label, col in columns.items():
        if col not in data:
            continue
        valid = data[["Tarih", col]].dropna()
        if valid.empty:
            continue
        color = (colors or SEGMENTS).get(label, "#475569")
        values = valid[col] / YP_SCALE
        fig.add_trace(go.Bar(
            x=valid["Tarih"], y=values, name=label,
            marker_color=color,
            customdata=[display_number(v) for v in values],
            hovertemplate="%{x|%d.%m.%Y}<br>%{customdata} milyar<extra>%{fullData.name}</extra>",
        ))
        x, y = valid.iloc[-1]["Tarih"], values.iloc[-1]
        fig.add_annotation(
            x=x, y=y, text=display_number(y), showarrow=True,
            arrowhead=0, ax=45, ay=(-30 if y >= 0 else 30),
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
        segment, f"{value / YP_SCALE:,.2f} milyar" if pd.notna(value) else "Veri yok",
        delta=f"{delta / YP_SCALE:+,.2f} milyar (haftalık)" if pd.notna(delta) else None,
    )
st.caption("Tutarlar milyar USD karşılığıdır. Toplam YP mevduat stok kartı gösterilmez.")

st.subheader("Haftalık Parite Etkisinden Arındırılmış Değişim")
parity_main = {
    "Toplam Yurt İçi Yerleşikler": "Parite Hariç - Yurt İçi Yerleşikler",
    "Gerçek Kişiler": "Parite Hariç - Gerçek Kişiler",
    "Tüzel Kişiler": "Parite Hariç - Tüzel Kişiler",
}
p1, p2, p3 = st.columns(3)
for widget, (segment, col) in zip((p1, p2, p3), parity_main.items()):
    value = last_valid(yp_df[col]) if col in yp_df else float("nan")
    widget.metric(segment, f"{value / YP_SCALE:+,.2f} milyar" if pd.notna(value) else "Veri yok")
st.caption("Toplam yurt içi yerleşikler TCMB'nin kendi serisidir; gerçek ve tüzel kişilerin hesaplanmış toplamı değildir. Birim: milyar USD karşılığı.")

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
    yp_df, {s: parity_main[s] for s in SEGMENTS}, "Haftalık Parite Hariç Değişim"
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
    "Altın": ("Altın", "Altın"),
}

st.subheader("Varlık Türüne Göre Analiz")
st.caption("Her varlık için mevduat seviyesi, haftalık nominal değişim ve parite hariç değişim gösterilir. Sağdaki etiketler son gözleme aittir. Birim: milyar USD karşılığı.")
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
    st.info("YTD için 1 Ocak'tan itibaren veri gerekir. Tarih aralığının başlangıcını 1 Ocak'a alın.")
else:
    ytd_data = yp_df[(yp_df["Tarih"] >= year_start) & (yp_df["Tarih"] <= latest_date)]
    ytd_rows = []
    ytd_fig = go.Figure()
    asset_colors = {
        "Gerçek Kişiler | USD": "#247BA0",
        "Gerçek Kişiler | EUR": "#16A34A",
        "Gerçek Kişiler | Altın": "#8B5CF6",
        "Tüzel Kişiler | USD": "#F28E2B",
        "Tüzel Kişiler | EUR": "#D9487D",
        "Tüzel Kişiler | Altın": "#64748B",
    }
    summary_by_segment = {segment: [] for segment in SEGMENTS}
    for segment in SEGMENTS:
        for asset in ("USD", "EUR", "Altın"):
            col = f"Parite Hariç - {segment} {asset}"
            if col not in ytd_data:
                continue
            valid = ytd_data[["Tarih", col]].dropna()
            if valid.empty:
                continue
            cumulative = valid[col].cumsum() / YP_SCALE
            total = float(cumulative.iloc[-1])
            name = f"{segment} | {asset}"
            color = asset_colors[name]
            ytd_rows.append({"Grup": segment, "Varlık": "XAU (Altın)" if asset == "Altın" else asset,
                             "YTD Parite Hariç (milyar USD karşılığı)": total})
            summary_by_segment[segment].append(f"{asset if asset != 'Altın' else 'XAU'} {total:+,.2f} milyar")
            ytd_fig.add_trace(go.Scatter(
                x=valid["Tarih"], y=cumulative,
                mode="lines", name=name,
                line=dict(width=2.6, color=color),
                hovertemplate="%{x|%d.%m.%Y}<br>%{y:+,.2f} milyar<extra>%{fullData.name}</extra>",
            ))
            ytd_fig.add_annotation(
                x=valid["Tarih"].iloc[-1], y=total, text=f"{total:+,.2f}",
                showarrow=False, xanchor="left", xshift=10,
                font=dict(size=11, color=color),
                bgcolor="rgba(255,255,255,0.95)", bordercolor=color, borderwidth=1,
            )
    if ytd_rows:
        st.markdown("**YTD parite etkisinden arındırılmış pozisyon değişimleri**")
        for segment, values in summary_by_segment.items():
            if values:
                st.markdown(f"**{segment}:** " + " · ".join(values))
        st.caption("Pozitif (+) değer artışı, negatif (−) değer azalışı gösterir. Bunlar dönem sonu stok pozisyonu değil, yılbaşından beri birikimli parite hariç değişimdir.")
        ytd_fig.update_layout(title=f"{latest_date.year} YTD — Kümülatif Parite Hariç Değişim")
        st.plotly_chart(style_chart(ytd_fig), use_container_width=True)
        ytd_table = pd.DataFrame(ytd_rows)
        ytd_table["YTD Parite Hariç (milyar USD karşılığı)"] = ytd_table[
            "YTD Parite Hariç (milyar USD karşılığı)"
        ].map(lambda value: f"{value:+,.2f}")
        st.dataframe(ytd_table, use_container_width=True, hide_index=True)
        email_figures.append(("ytd_birikimli_parite_haric", ytd_fig))
        st.caption("YTD, yılbaşından son yayımlanan gözleme kadar haftalık EVDS parite hariç değişimlerinin toplamıdır. Değerler milyar USD karşılığıdır; varlık isimleri USD/EUR/XAU kırılımını gösterir.")
    else:
        st.warning("YTD hesaplaması için gerekli haftalık seriler bulunamadı.")

st.subheader("Son Haftanın Sayısal Özeti")
summary_table = pd.DataFrame(summary_rows)
for col in ("Seviye", "Nominal", "Parite Hariç", "Parite Etkisi"):
    summary_table[f"{col} (milyar USD karşılığı)"] = summary_table[col].map(
        lambda value: f"{value / YP_SCALE:+,.2f}" if pd.notna(value) else "Veri yok"
    )
summary_table = summary_table.drop(columns=["Seviye", "Nominal", "Parite Hariç", "Parite Etkisi"])
st.dataframe(summary_table, use_container_width=True, hide_index=True)
st.caption("Nominal = stok serisinin haftalık farkı. Parite Hariç ve Parite Etkisi = TCMB'nin ayrı haftalık EVDS serileri. Bu sütunlar otomatik olarak birbirine eşit kabul edilmez.")

st.subheader("Detaylı Veri ve CSV")
st.caption("Verileri müşteri grubu ve gösterim türüne göre filtreleyebilirsiniz. Tutarlar **milyar USD karşılığı** cinsindedir.")

yp_detail_groups = {
    "Genel": ["Yurt İçi Yerleşikler", "Gerçek Kişiler", "Tüzel Kişiler"],
    "Gerçek Kişiler": ["Gerçek Kişiler", "Gerçek Kişiler - USD", "Gerçek Kişiler - EUR", "Gerçek Kişiler - Altın"],
    "Tüzel Kişiler": ["Tüzel Kişiler", "Tüzel Kişiler - USD", "Tüzel Kişiler - EUR", "Tüzel Kişiler - Altın"],
}
yp_group_col, yp_type_col = st.columns(2)
with yp_group_col:
    yp_detail_group = st.selectbox("Müşteri grubu", list(yp_detail_groups), key="yp_detail_group")
with yp_type_col:
    yp_detail_type = st.selectbox(
        "Gösterim", ["Mevduat Stoku", "Haftalık Nominal Değişim", "Haftalık Parite Hariç Değişim", "Haftalık Parite Etkisi"],
        key="yp_detail_type"
    )

yp_selected_names = yp_detail_groups[yp_detail_group]
yp_detail = pd.DataFrame({"Tarih": yp_df["Tarih"]})
for yp_name in yp_selected_names:
    if yp_detail_type == "Mevduat Stoku":
        yp_source = yp_name
    elif yp_detail_type == "Haftalık Nominal Değişim":
        yp_source = yp_name
    else:
        yp_prefix = "Parite Hariç - " if yp_detail_type == "Haftalık Parite Hariç Değişim" else "Parite Etkisi - "
        yp_source = yp_prefix + yp_name.replace(" - ", " ")
        # Genel toplamların EVDS adları tire içerir; varlık bazlı seriler içermez.
        if yp_name in ("Yurt İçi Yerleşikler", "Gerçek Kişiler", "Tüzel Kişiler"):
            yp_source = yp_prefix + yp_name
    if yp_source not in yp_df.columns:
        continue
    yp_values = pd.to_numeric(yp_df[yp_source], errors="coerce")
    if yp_detail_type == "Haftalık Nominal Değişim":
        yp_values = yp_values.diff()
    yp_detail[yp_name] = yp_values / YP_SCALE

yp_detail = yp_detail.sort_values("Tarih", ascending=False).reset_index(drop=True)
yp_detail["Tarih"] = pd.to_datetime(yp_detail["Tarih"]).dt.strftime("%d.%m.%Y")
yp_value_cols = [c for c in yp_detail.columns if c != "Tarih"]
yp_signed = yp_detail_type != "Mevduat Stoku"
yp_column_config = {
    name: st.column_config.NumberColumn(
        name, help="Milyar USD karşılığı", format="%+.2f" if yp_signed else "%.2f", width="medium"
    ) for name in yp_value_cols
}
st.dataframe(
    yp_detail, use_container_width=True, hide_index=True, height=390,
    column_config={"Tarih": st.column_config.TextColumn("Tarih", width="small"), **yp_column_config},
)
st.caption("+ artış, − azalış anlamına gelir. Boş hücreler EVDS'de ilgili gözlemin bulunmadığını gösterir.")

yp_csv_col, yp_full_csv_col = st.columns(2)
with yp_csv_col:
    st.download_button(
        "Görüntülenen Tabloyu İndir (CSV)",
        data=yp_detail.to_csv(index=False, float_format="%.2f").encode("utf-8-sig"),
        file_name="yp_mevduat_secili_veri.csv", mime="text/csv", key="yp_filtered_csv",
        use_container_width=True,
    )
with yp_full_csv_col:
    st.download_button(
        "Tüm Ham Veriyi İndir (CSV)",
        data=yp_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="yp_mevduat_tum_veriler.csv", mime="text/csv", key="yp_full_csv",
        use_container_width=True,
    )

# =========================================================
# ÜST YÖNETİM E-POSTASI
# =========================================================

def build_management_email(report_df, observation_date, period_start, dashboard_url=""):
    """
    E-posta içeriğini yalnızca EVDS'den gelen rakamlarla hazırlar.
    Stok: son gözlem, haftalık: aynı gözlemdeki parite hariç akım,
    YTD: 1 Ocak'tan son gözleme haftalık akımların toplamı.
    """
    assets = (("USD", "USD"), ("EUR", "EUR"), ("XAU (Altın)", "Altın"))
    segments = ("Gerçek Kişiler", "Tüzel Kişiler")
    period = report_df.loc[
        (report_df["Tarih"] >= period_start)
        & (report_df["Tarih"] <= observation_date)
    ].sort_values("Tarih")
    rows = []
    for segment in segments:
        for label, suffix in assets:
            level_col = f"{segment} - {suffix}"
            change_col = f"Parite Hariç - {segment} {suffix}"
            stock = (
                last_valid(report_df.loc[
                    report_df["Tarih"] <= observation_date, level_col
                ]) if level_col in report_df else float("nan")
            )
            weekly = (
                last_valid(report_df.loc[
                    report_df["Tarih"] <= observation_date, change_col
                ]) if change_col in report_df else float("nan")
            )
            flows = (
                pd.to_numeric(period[change_col], errors="coerce").dropna()
                if change_col in period else pd.Series(dtype=float)
            )
            ytd = flows.sum() if not flows.empty else float("nan")
            rows.append({
                "segment": segment, "asset": label,
                "stock": stock / YP_SCALE,
                "weekly": weekly / YP_SCALE,
                "ytd": ytd / YP_SCALE,
            })

    def num(value, signed=False):
        if pd.isna(value):
            return "—"
        return f"{value:{'+' if signed else ''},.2f}"

    def colored(value):
        if pd.isna(value):
            return '<span style="color:#94a3b8">—</span>'
        color = "#13795b" if value > 0 else "#b42318" if value < 0 else "#475569"
        return f'<span style="font-weight:700;color:{color}">{num(value, True)}</span>'

    def plain_summary(segment):
        items = [r for r in rows if r["segment"] == segment]
        return "; ".join(
            f'{r["asset"]} {num(r["ytd"], True)}'
            for r in items
        )

    def html_summary(segment):
        items = [r for r in rows if r["segment"] == segment]
        return " &nbsp;·&nbsp; ".join(
            f'<strong>{escape(r["asset"])}</strong> {colored(r["ytd"])}'
            for r in items
        )

    def html_weekly_summary(segment):
        items = [r for r in rows if r["segment"] == segment]
        return " &nbsp;·&nbsp; ".join(
            f'<strong>{escape(r["asset"])}</strong> {colored(r["weekly"])}'
            for r in items
        )

    header = (
        f"YP Mevduat | Haftalık Analiz | {observation_date:%d.%m.%Y}"
    )
    intro = (
        "Gerçek ve tüzel kişilerin USD, EUR ve altın mevduat stokları, "
        "haftalık parite etkisinden arındırılmış değişimleri ve "
        f"{period_start:%d.%m.%Y} tarihinden itibaren birikimli "
        "parite hariç değişimleri aşağıda sunulmaktadır."
    )
    text_rows = [
        f'{r["segment"]} | {r["asset"]} | '
        f'Stok: {num(r["stock"])} | '
        f'Haftalık: {num(r["weekly"], True)} | '
        f'YTD: {num(r["ytd"], True)}'
        for r in rows
    ]
    plain = (
        "Merhaba,\n\n" + intro
        + "\n\nBİRİM: MİLYAR USD KARŞILIĞI\n\n"
        + "\n".join(text_rows)
        + "\n\nYTD PARİTE HARİÇ DEĞİŞİM\n"
        + "Gerçek Kişiler: " + plain_summary("Gerçek Kişiler")
        + "\nTüzel Kişiler: " + plain_summary("Tüzel Kişiler")
        + "\n\nNot: Stoklar dönem sonu bakiyesidir. Haftalık ve YTD "
          "rakamları parite etkisinden arındırılmış değişimdir; "
          "YTD stok bakiyesi değildir. (+) artış, (-) azalıştır. "
          "Eksik EVDS verileri — ile gösterilir. "
          "YTD haftalık serilerin toplamıdır.\n\n"
          "Bilgilerinize sunulur.\n\nSaygılarımla,\n"
    )

    if dashboard_url:
        plain += "\nDashboard üzerinden detaylı analiz: " + dashboard_url + "\n"
        dashboard_html = (
            '<div style="margin:26px 0 10px;padding:18px 20px;'
            'background:#edf3fb;border:1px solid #d6e3f4;border-radius:8px;">'
            '<div style="font-size:13px;font-weight:bold;color:#24466d;margin-bottom:8px;">'
            '&#8594; &nbsp; DETAYLI ANALİZ</div>'
            '<div style="font-size:13px;color:#52647c;margin-bottom:12px;">'
            'Güncel grafiklere ve ayrıntılı veri kırılımlarına dashboard üzerinden ulaşabilirsiniz.</div>'
            '<a href="' + escape(dashboard_url, quote=True) + '" '
            'style="display:inline-block;background:#173b63;color:#ffffff;'
            'text-decoration:none;font-weight:bold;font-size:13px;'
            'padding:11px 18px;border-radius:6px;">Dashboard’u Aç</a>'
            '</div>'
        )
    else:
        dashboard_html = ""

    table_rows = []
    for idx, r in enumerate(rows):
        background = "#f7f9fc" if idx % 2 == 0 else "#ffffff"
        border = "border-top:2px solid #cbd5e1;" if idx == 3 else ""
        table_rows.append(
            f'<tr style="background:{background};{border}">'
            f'<td style="padding:12px 10px;border-bottom:1px solid #e5eaf1;">'
            f'<strong>{escape(r["segment"])}</strong></td>'
            f'<td style="padding:12px 10px;border-bottom:1px solid #e5eaf1;">'
            f'<strong>{escape(r["asset"])}</strong></td>'
            f'<td align="right" style="padding:12px 10px;border-bottom:1px solid #e5eaf1;'
            f'white-space:nowrap;font-weight:600;color:#21344d;">{num(r["stock"])}</td>'
            f'<td align="right" style="padding:12px 10px;border-bottom:1px solid #e5eaf1;'
            f'white-space:nowrap;">{colored(r["weekly"])}</td>'
            f'<td align="right" style="padding:12px 10px;border-bottom:1px solid #e5eaf1;'
            f'white-space:nowrap;">{colored(r["ytd"])}</td></tr>'
        )

    html = f"""<!DOCTYPE html>
<html lang="tr"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:28px 12px;background:#f2f5fa;
font-family:Arial,Helvetica,sans-serif;color:#172b4d;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0"
style="width:100%;max-width:850px;margin:auto;background:#fff;border:1px solid #e1e7f0;
border-radius:12px;">
<tr><td style="background:#142c4c;padding:30px 34px;color:#fff;">
<div style="font-size:12px;letter-spacing:2px;color:#a9c5e5;font-weight:bold;">
HAFTALIK MEVDUAT ANALİZİ</div>
<h1 style="font-size:25px;line-height:1.25;margin:12px 0 8px;color:#fff;">
Yabancı Para Mevduatları</h1>
<div style="font-size:14px;color:#dce8f7;">Haftalık Rapor &nbsp;|&nbsp;
Veri tarihi: {observation_date:%d.%m.%Y}</div>
</td></tr>
<tr><td style="padding:28px 34px 10px;">
<p style="font-size:14px;line-height:1.7;margin:0 0 20px;">
Merhaba,<br><br>{escape(intro)}</p>
<div style="font-size:13px;font-weight:bold;color:#24466d;margin:22px 0 12px;">
&#8594; &nbsp; MEVDUAT STOKLARI VE DEĞİŞİMLER</div>
<div style="font-size:12px;color:#64748b;margin-bottom:10px;">
Tüm tutarlar <strong>milyar USD karşılığıdır</strong>.
Stok = rapor tarihindeki bakiye; haftalık / YTD = parite etkisi hariç değişim.</div>
<table cellpadding="0" cellspacing="0" border="0"
style="width:100%;border-collapse:collapse;font-size:13px;">
<thead><tr style="background:#dce6f2;color:#172f50;">
<th align="left" style="padding:12px 10px;">Müşteri grubu</th>
<th align="left" style="padding:12px 10px;">Varlık</th>
<th align="right" style="padding:12px 10px;">Stok</th>
<th align="right" style="padding:12px 10px;">Haftalık</th>
<th align="right" style="padding:12px 10px;">YTD</th>
</tr></thead><tbody>{''.join(table_rows)}</tbody></table>
<div style="font-size:13px;font-weight:bold;color:#24466d;margin:30px 0 14px;">
&#8594; &nbsp; GRAFİKLERLE HAFTALIK GÖRÜNÜM</div>
<p style="font-size:12px;color:#64748b;margin:0 0 12px;">Mevduat stokları ve parite etkisinden arındırılmış haftalık değişim</p>
<div style="font-size:12px;color:#64748b;margin:0 0 8px;">Haftalık parite hariç değişim (milyar USD karşılığı)</div>
<div style="padding:12px 14px;background:#f3f7fc;border-left:3px solid #247ba0;margin-bottom:8px;font-size:13px;line-height:1.8;">
<strong>Gerçek Kişiler</strong><br>{html_weekly_summary("Gerçek Kişiler")}</div>
<div style="padding:12px 14px;background:#f3f7fc;border-left:3px solid #f28e2b;margin-bottom:16px;font-size:13px;line-height:1.8;">
<strong>Tüzel Kişiler</strong><br>{html_weekly_summary("Tüzel Kişiler")}</div>
<img src="cid:{{stock_chart}}" alt="Gerçek ve tüzel kişi mevduat stokları" width="740" style="display:block;width:100%;max-width:740px;height:auto;margin:12px 0 22px;border:1px solid #e3e9f1;border-radius:8px;">
<img src="cid:{{weekly_chart}}" alt="Haftalık parite hariç değişim" width="740" style="display:block;width:100%;max-width:740px;height:auto;margin:12px 0 22px;border:1px solid #e3e9f1;border-radius:8px;">
<div style="font-size:13px;font-weight:bold;color:#24466d;margin:30px 0 14px;">
&#8594; &nbsp; YILBAŞINDAN BUGÜNE PARİTE HARİÇ DEĞİŞİM</div>
<div style="padding:14px 16px;background:#f3f7fc;border-left:3px solid #247ba0;
margin-bottom:10px;font-size:13px;line-height:1.8;">
<strong>Gerçek Kişiler</strong><br>{html_summary("Gerçek Kişiler")}</div>
<div style="padding:14px 16px;background:#f3f7fc;border-left:3px solid #f28e2b;
font-size:13px;line-height:1.8;">
<strong>Tüzel Kişiler</strong><br>{html_summary("Tüzel Kişiler")}</div>
<img src="cid:{{ytd_chart}}" alt="Yılbaşından bugüne birikimli parite hariç değişim" width="740" style="display:block;width:100%;max-width:740px;height:auto;margin:20px 0 24px;border:1px solid #e3e9f1;border-radius:8px;">
{dashboard_html}
<div style="font-size:13px;font-weight:bold;font-style:italic;color:#64748b;margin:30px 0 12px;">
&#8594; &nbsp; Metodoloji notu</div>
<p style="font-size:12px;color:#52647c;line-height:1.7;font-style:italic;">
YTD dönemi: {period_start:%d.%m.%Y}–{observation_date:%d.%m.%Y}.
YTD tutarlar, ilgili TCMB EVDS haftalık parite hariç değişim serilerinin
birikimli toplamıdır. Stok tutarlarıyla doğrudan eşitlenmemelidir.
Artı (+) artışı, eksi (−) azalışı gösterir. Eksik veriler — ile gösterilir.
Varlık kırılımları USD, EUR ve XAU'dur; tutarlar USD karşılığı bazındadır.</p>
<p style="font-size:14px;line-height:1.7;margin:24px 0 22px;">
Bilgilerinize sunulur.<br><br>Saygılarımla,</p>
</td></tr>
<tr><td style="background:#f2f5fa;padding:16px 34px;font-size:11px;
color:#64748b;">Kaynak: TCMB EVDS &nbsp;•&nbsp; Otomatik oluşturulan mevduat analiz raporu
&nbsp;•&nbsp; {observation_date:%d.%m.%Y}</td></tr>
</table></body></html>"""
    return header, plain, html


st.subheader("E-posta Raporu")
st.caption(
    "HTML e-posta: gerçek/tüzel kişi bazında "
    "USD, EUR ve XAU stokları, haftalık ve YTD parite hariç değişimleri. "
    "Özet grafikler PNG eki olarak gönderilir."
)
if st.button("E-posta Gönder", type="primary"):
    try:
        year_start = pd.Timestamp(latest_date.year, 1, 1)
        # Seçili tarih aralığı yılbaşından sonra başlıyorsa,
        # YTD'yi eksik hesaplamamak için yılbaşından itibaren ayrıca çek.
        if yp_df["Tarih"].min() > year_start:
            with st.spinner("Tam yılbaşından bugüne veri hazırlanıyor..."):
                mail_df, _ = fetch_evds_data(
                    year_start.strftime("%d-%m-%Y"),
                    latest_date.strftime("%d-%m-%Y"),
                    tuple(all_yp_series.items()),
                )
        else:
            mail_df = yp_df
        subject, plain_body, html_body = build_management_email(
            mail_df, latest_date, year_start, DASHBOARD_URL
        )
        # Yönetime okunabilir bir e-posta: esas tablo mesaj gövdesinde;
        # yalnızca özet grafikler ekte.
        # Grafikler hem e-postanın içinde görünür hem PNG eki olarak saklanır.
        inline_images = [
            ("stock_chart", fig_to_png(fig_main)),
            ("weekly_chart", fig_to_png(fig_adjusted)),
        ]
        if "ytd_fig" in globals() and len(ytd_fig.data) > 0:
            inline_images.append(("ytd_chart", fig_to_png(ytd_fig)))
        else:
            # Eksik YTD grafiği varsa kırık görsel yerine açıklama göster.
            html_body = html_body.replace(
                '<img src="cid:{{ytd_chart}}" alt="Yılbaşından bugüne birikimli parite hariç değişim" width="740" style="display:block;width:100%;max-width:740px;height:auto;margin:20px 0 24px;border:1px solid #e3e9f1;border-radius:8px;">',
                '<p style="color:#64748b;font-size:12px;">YTD grafik verisi bulunamadı.</p>',
            )
        attachments = [(f"{name}.png", png) for name, png in inline_images]
        send_email(
            subject, plain_body, attachments,
            html_body=html_body, inline_images=inline_images,
        )
        st.success("E-posta başarıyla gönderildi.")
    except Exception as exc:
        st.error(f"E-posta gönderilemedi: {exc}")

