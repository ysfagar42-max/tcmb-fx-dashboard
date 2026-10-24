import smtplib
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

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

st.title("Mevduat Analiz Dashboard")
st.caption("TCMB EVDS verileriyle mevduat analizi")


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
        "Önbellek süresi: 1 saat"
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


def fig_to_png(fig):
    return fig.to_image(
        format="png",
        width=1400,
        height=700,
        scale=2,
    )


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
    default_start = today - timedelta(days=365)

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

    return (
        start_date.strftime("%d-%m-%Y"),
        end_date.strftime("%d-%m-%Y"),
    )


# =========================================================
# PANEL SEÇİMİ
# =========================================================

panel = st.radio(
    "Analiz paneli",
    ["YP DTH", "TL Mevduat"],
    horizontal=True,
)


# =========================================================
# TL MEVDUAT PANELİ
# =========================================================

if panel == "TL Mevduat":

    st.header("TL Mevduat Analizi")
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

    st.subheader("Genel Görünüm")
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
        "Seviyeler trilyon TL, değişim tutarları milyar TL olarak gösterilir."
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

    st.subheader("Haftalık Değişim Tablosu")

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

    st.subheader("4 Haftalık Değişim Tablosu")

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

    st.subheader("13 Haftalık Değişim Tablosu")

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

    st.subheader("Veri İndirme")

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
        "TL Mevduat CSV İndir",
        data=csv_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="tl_mevduat_analiz.csv",
        mime="text/csv",
    )

    st.subheader("Rapor Gönderimi")

    if st.button("TL Mevduat Raporunu E-posta ile Gönder"):
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
                "TL Mevduat Analiz Raporu",
                "TL Mevduat Analiz Dashboard raporu ektedir.",
                attachments,
            )
            st.success("E-posta başarıyla gönderildi.")

        except Exception as e:
            st.error(f"E-posta gönderilemedi: {e}")

    st.stop()


# =========================================================
# YP DTH PANELİ
# =========================================================

st.header("YP DTH Analizi")
start_date, end_date = show_date_filters("yp")

all_yp_series = {
    **YP_LEVEL_SERIES,
    **YP_CHANGE_SERIES,
}

with st.spinner("YP DTH verileri getiriliyor..."):
    try:
        yp_df, yp_fetched_at = fetch_evds_data(
            start_date,
            end_date,
            tuple(all_yp_series.items()),
        )
    except Exception as e:
        st.error(f"YP DTH verileri alınamadı: {e}")
        st.stop()

show_data_status(yp_df, yp_fetched_at)

if yp_df.empty:
    st.error("Seçilen tarih aralığında YP verisi bulunamadı.")
    st.stop()

required_columns = [
    "Toplam YP Mevduat",
    "Gerçek Kişiler",
    "Tüzel Kişiler",
]

missing_columns = [c for c in required_columns if c not in yp_df.columns]

if missing_columns:
    st.error(
        "YP serilerinden bazıları bulunamadı: "
        + ", ".join(missing_columns)
        + ". EVDS seri kodlarını ve API yanıtını kontrol et."
    )
    st.stop()

yp_df = yp_df.sort_values("Tarih").reset_index(drop=True)
yp_latest = yp_df.iloc[-1]

# ---------------------------------------------------------
# SEVİYE KARTLARI: SADECE TOPLAM / GERÇEK / TÜZEL
# ---------------------------------------------------------

st.subheader(
    f"Mevduat Seviyeleri — {yp_latest['Tarih'].strftime('%d.%m.%Y')}"
)

c1, c2, c3 = st.columns(3)

c1.metric(
    "Toplam YP Mevduat",
    f"{yp_latest['Toplam YP Mevduat']:,.2f}",
)

c2.metric(
    "Gerçek Kişiler",
    f"{yp_latest['Gerçek Kişiler']:,.2f}",
)

c3.metric(
    "Tüzel Kişiler",
    f"{yp_latest['Tüzel Kişiler']:,.2f}",
)


# ---------------------------------------------------------
# ANA GRAFİK: TOPLAM / GERÇEK / TÜZEL
# ---------------------------------------------------------

st.subheader("Toplam YP Mevduat, Gerçek Kişiler ve Tüzel Kişiler")

main_columns = [
    "Toplam YP Mevduat",
    "Gerçek Kişiler",
    "Tüzel Kişiler",
]

main_long = yp_df[["Tarih"] + main_columns].melt(
    id_vars="Tarih",
    var_name="Mevduat Grubu",
    value_name="Tutar",
)

fig_yp = px.line(
    main_long,
    x="Tarih",
    y="Tutar",
    color="Mevduat Grubu",
    color_discrete_map=COLORS,
    title="YP Mevduat Seviyeleri",
    labels={
        "Tarih": "Tarih",
        "Tutar": "Seri değeri",
        "Mevduat Grubu": "Mevduat Grubu",
    },
)

fig_yp.update_traces(line=dict(width=3))
fig_yp.update_layout(
    hovermode="x unified",
    legend_title_text="Mevduat Grubu",
)
st.plotly_chart(fig_yp, use_container_width=True)


# ---------------------------------------------------------
# ANA GRUPLARIN HAFTALIK NOMİNAL DEĞİŞİMİ
# ---------------------------------------------------------

st.subheader("Toplam, Gerçek ve Tüzel Kişiler — Haftalık Nominal Değişim")

delta_df = yp_df[["Tarih"] + main_columns].copy()

for col in main_columns:
    delta_df[col] = delta_df[col].diff()

delta_long = delta_df.melt(
    id_vars="Tarih",
    var_name="Mevduat Grubu",
    value_name="Haftalık Nominal Değişim",
)

fig_main_delta = px.bar(
    delta_long,
    x="Tarih",
    y="Haftalık Nominal Değişim",
    color="Mevduat Grubu",
    color_discrete_map=COLORS,
    barmode="group",
    title="Haftalık Nominal Değişim",
    labels={
        "Tarih": "Tarih",
        "Haftalık Nominal Değişim": "Seri değerindeki değişim",
        "Mevduat Grubu": "Mevduat Grubu",
    },
)

fig_main_delta.update_layout(legend_title_text="Mevduat Grubu")
st.plotly_chart(fig_main_delta, use_container_width=True)


# ---------------------------------------------------------
# USD / EUR / DİĞER DÖVİZ / ALTIN KIRILIMLARI
# ---------------------------------------------------------

st.subheader("USD, EUR, Diğer Döviz ve Altın Kırılımı")

st.caption(
    "Her grafikte gerçek kişiler ve tüzel kişiler ayrı çizgilerle gösterilir. "
    "Haftalık değişim, ilgili seviye serisinin son iki gözlemi arasındaki "
    "fark olarak hesaplanır."
)

BREAKDOWN = {
    "USD": {
        "individual": "Gerçek Kişiler - USD",
        "corporate": "Tüzel Kişiler - USD",
        "unit": "USD serisinin yayımlanan birimi",
        "adjusted_individual": "Parite Hariç - Gerçek Kişiler USD",
        "adjusted_corporate": "Parite Hariç - Tüzel Kişiler USD",
        "parity_individual": "Parite Etkisi - Gerçek Kişiler USD",
        "parity_corporate": "Parite Etkisi - Tüzel Kişiler USD",
    },
    "EUR": {
        "individual": "Gerçek Kişiler - EUR",
        "corporate": "Tüzel Kişiler - EUR",
        "unit": "EUR serisinin yayımlanan birimi",
        "adjusted_individual": "Parite Hariç - Gerçek Kişiler EUR",
        "adjusted_corporate": "Parite Hariç - Tüzel Kişiler EUR",
        "parity_individual": "Parite Etkisi - Gerçek Kişiler EUR",
        "parity_corporate": "Parite Etkisi - Tüzel Kişiler EUR",
    },
    "Diğer Döviz": {
        "individual": "Gerçek Kişiler - Diğer Döviz",
        "corporate": "Tüzel Kişiler - Diğer Döviz",
        "unit": "Serinin yayımlanan birimi",
        "adjusted_individual": "Parite Hariç - Gerçek Kişiler Diğer Döviz",
        "adjusted_corporate": "Parite Hariç - Tüzel Kişiler Diğer Döviz",
        "parity_individual": "Parite Etkisi - Gerçek Kişiler Diğer Döviz",
        "parity_corporate": "Parite Etkisi - Tüzel Kişiler Diğer Döviz",
    },
    "Altın": {
        "individual": "Gerçek Kişiler - Altın",
        "corporate": "Tüzel Kişiler - Altın",
        "unit": "Altın serisinin yayımlanan birimi",
        "adjusted_individual": "Parite Hariç - Gerçek Kişiler Altın",
        "adjusted_corporate": "Parite Hariç - Tüzel Kişiler Altın",
        "parity_individual": "Parite Etkisi - Gerçek Kişiler Altın",
        "parity_corporate": "Parite Etkisi - Tüzel Kişiler Altın",
    },
}

breakdown_rows = []
level_figures = []
delta_figures = []
parity_figures = []

for asset, cfg in BREAKDOWN.items():

    individual_col = cfg["individual"]
    corporate_col = cfg["corporate"]

    # Her varlık için seviye grafiği
    available = [
        col for col in [individual_col, corporate_col]
        if col in yp_df.columns
    ]

    if available:
        level_long = yp_df[["Tarih"] + available].melt(
            id_vars="Tarih",
            var_name="Seri",
            value_name="Tutar",
        )

        # Seri adlarını "USD" gibi aynı etikete çevirmiyoruz.
        # Böylece gerçek/tüzel ayrımı grafikte kaybolmuyor.
        label_map = {
            individual_col: "Gerçek Kişiler",
            corporate_col: "Tüzel Kişiler",
        }
        level_long["Mevduat Sahibi"] = level_long["Seri"].map(label_map)

        fig_level = px.line(
            level_long,
            x="Tarih",
            y="Tutar",
            color="Mevduat Sahibi",
            color_discrete_map=SEGMENT_COLORS,
            title=f"{asset} — Mevduat Seviyesi",
            labels={
                "Tarih": "Tarih",
                "Tutar": cfg["unit"],
                "Mevduat Sahibi": "Mevduat Sahibi",
            },
        )
        fig_level.update_traces(line=dict(width=3))
        fig_level.update_layout(
            hovermode="x unified",
            legend_title_text="Mevduat Sahibi",
        )
        level_figures.append((asset, fig_level))

    # Haftalık nominal delta grafiği
    delta_rows = []

    for segment, level_col in [
        ("Gerçek Kişiler", individual_col),
        ("Tüzel Kişiler", corporate_col),
    ]:
        if level_col in yp_df.columns:
            temp = yp_df[["Tarih", level_col]].copy()
            temp["Haftalık Nominal Değişim"] = temp[level_col].diff()
            temp["Mevduat Sahibi"] = segment

            delta_rows.append(
                temp[["Tarih", "Haftalık Nominal Değişim", "Mevduat Sahibi"]]
            )

    if delta_rows:
        delta_long_asset = pd.concat(delta_rows, ignore_index=True)

        fig_delta = px.bar(
            delta_long_asset,
            x="Tarih",
            y="Haftalık Nominal Değişim",
            color="Mevduat Sahibi",
            color_discrete_map=SEGMENT_COLORS,
            barmode="group",
            title=f"{asset} — Haftalık Nominal Değişim",
            labels={
                "Tarih": "Tarih",
                "Haftalık Nominal Değişim": cfg["unit"],
                "Mevduat Sahibi": "Mevduat Sahibi",
            },
        )
        fig_delta.update_layout(legend_title_text="Mevduat Sahibi")
        delta_figures.append((asset, fig_delta))

    # Tablo için son seviye ve haftalık değişim
    for segment, level_col, adjusted_col, parity_col in [
        (
            "Gerçek Kişiler",
            individual_col,
            cfg["adjusted_individual"],
            cfg["parity_individual"],
        ),
        (
            "Tüzel Kişiler",
            corporate_col,
            cfg["adjusted_corporate"],
            cfg["parity_corporate"],
        ),
    ]:
        breakdown_rows.append({
            "Döviz / Varlık": asset,
            "Mevduat Sahibi": segment,
            "Mevcut Seviye": latest_value(yp_df, level_col),
            "Haftalık Nominal Değişim": latest_difference(yp_df, level_col),
            "Parite Hariç Değişim": latest_value(yp_df, adjusted_col),
            "Parite Etkisi": latest_value(yp_df, parity_col),
        })

    # Parite hariç değişim ve parite etkisini iki segment için ayrı grafikle
    parity_rows = []

    for segment, adjusted_col, parity_col in [
        (
            "Gerçek Kişiler",
            cfg["adjusted_individual"],
            cfg["parity_individual"],
        ),
        (
            "Tüzel Kişiler",
            cfg["adjusted_corporate"],
            cfg["parity_corporate"],
        ),
    ]:
        for series_name, col_name in [
            ("Parite Hariç Değişim", adjusted_col),
            ("Parite Etkisi", parity_col),
        ]:
            if col_name in yp_df.columns:
                temp = yp_df[["Tarih", col_name]].copy()
                temp["Değişim Türü"] = series_name
                temp["Mevduat Sahibi"] = segment
                temp = temp.rename(columns={col_name: "Değer"})
                parity_rows.append(temp)

    if parity_rows:
        parity_long = pd.concat(parity_rows, ignore_index=True)

        fig_parity = px.bar(
            parity_long,
            x="Tarih",
            y="Değer",
            color="Değişim Türü",
            facet_row="Mevduat Sahibi",
            barmode="group",
            title=f"{asset} — Parite Hariç Değişim ve Parite Etkisi",
            labels={
                "Tarih": "Tarih",
                "Değer": "Seri değeri",
                "Değişim Türü": "Değişim Türü",
            },
        )
        fig_parity.update_layout(hovermode="x unified")
        parity_figures.append((asset, fig_parity))


# Seviye grafikleri
st.markdown("#### Mevduat Seviyeleri")

for asset, fig in level_figures:
    st.plotly_chart(fig, use_container_width=True)

# Haftalık nominal delta grafikleri
st.markdown("#### Haftalık Nominal Değişimler")

for asset, fig in delta_figures:
    st.plotly_chart(fig, use_container_width=True)

# Son hafta tablosu
st.markdown("#### Son Haftanın Sayısal Özeti")

breakdown_df = pd.DataFrame(breakdown_rows)

st.dataframe(
    breakdown_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Mevcut Seviye": st.column_config.NumberColumn(
            "Mevcut Seviye",
            format="%,.2f",
        ),
        "Haftalık Nominal Değişim": st.column_config.NumberColumn(
            "Haftalık Nominal Değişim",
            format="%+,.2f",
        ),
        "Parite Hariç Değişim": st.column_config.NumberColumn(
            "Parite Hariç Değişim",
            format="%+,.2f",
        ),
        "Parite Etkisi": st.column_config.NumberColumn(
            "Parite Etkisi",
            format="%+,.2f",
        ),
    },
)

st.caption(
    "Haftalık nominal değişim, ilgili seviyenin son iki gözlemi arasındaki "
    "farkıdır. Parite hariç değişim ve parite etkisi ilgili EVDS serilerinden "
    "alınır. Birimlerin doğru yorumlanması için EVDS serisinin açıklamasındaki "
    "ölçü birimi esas alınmalıdır."
)

# Parite grafikleri ayrı bölümde
with st.expander("Parite etkisi ayrıntılı grafikleri"):
    for asset, fig in parity_figures:
        st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------
# VERİ TABLOSU VE CSV
# ---------------------------------------------------------

st.subheader("YP Mevduat Verileri")

st.dataframe(
    yp_df.sort_values("Tarih", ascending=False),
    use_container_width=True,
    hide_index=True,
)

st.download_button(
    "YP DTH CSV İndir",
    data=yp_df.to_csv(index=False).encode("utf-8-sig"),
    file_name="yp_dth_analiz.csv",
    mime="text/csv",
)


# ---------------------------------------------------------
# E-POSTA RAPORU
# ---------------------------------------------------------

st.subheader("Rapor Gönderimi")

if st.button("YP DTH Raporunu E-posta ile Gönder"):
    try:
        attachments = [
            ("yp_toplam_gercek_tuzel.png", fig_to_png(fig_yp)),
            ("yp_ana_gruplar_haftalik_delta.png", fig_to_png(fig_main_delta)),
        ]

        for asset, fig in level_figures:
            attachments.append(
                (f"{asset.lower().replace(' ', '_')}_seviye.png", fig_to_png(fig))
            )

        for asset, fig in delta_figures:
            attachments.append(
                (
                    f"{asset.lower().replace(' ', '_')}_haftalik_delta.png",
                    fig_to_png(fig),
                )
            )

        send_email(
            "YP DTH Analiz Raporu",
            (
                "YP DTH Analiz Dashboard raporu ektedir.\n\n"
                "Raporda toplam YP mevduat, gerçek kişiler, tüzel kişiler, "
                "USD/EUR/diğer döviz/altın seviyeleri ve haftalık nominal "
                "değişimler yer almaktadır."
            ),
            attachments,
        )

        st.success("E-posta başarıyla gönderildi.")

    except Exception as e:
        st.error(
            "E-posta gönderilemedi. Grafiklerin PNG olarak dışa aktarılması "
            "için Kaleido kurulumu gerekebilir. Hata: "
            f"{e}"
        )
