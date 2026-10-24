import io
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
# YP DTH SEVİYE SERİLERİ
# =========================================================

YP_LEVEL_SERIES = {
    "Toplam YP Mevduat": "TP.HPBITABLO4.1",
    "Yurt İçi Yerleşikler": "TP.HPBITABLO4.2",
    "Gerçek Kişiler": "TP.HPBITABLO4.3",
    "Gerçek Kişiler - USD": "TP.HPBITABLO4.4",
    "Gerçek Kişiler - EUR": "TP.HPBITABLO4.5",
    "Gerçek Kişiler - Diğer": "TP.HPBITABLO4.6",
    "Gerçek Kişiler - Altın": "TP.HPBITABLO4.7",
    "Tüzel Kişiler": "TP.HPBITABLO4.8",
    "Tüzel Kişiler - USD": "TP.HPBITABLO4.9",
    "Tüzel Kişiler - EUR": "TP.HPBITABLO4.10",
    "Tüzel Kişiler - Diğer": "TP.HPBITABLO4.11",
    "Tüzel Kişiler - Altın": "TP.HPBITABLO4.12",
    "Yurt İçi Yerleşik Bankalar": "TP.HPBITABLO4.13",
    "Yurt Dışı Yerleşikler": "TP.HPBITABLO4.16",
    "Yurt Dışı Yerleşikler - USD": "TP.HPBITABLO4.17",
    "Yurt Dışı Yerleşikler - EUR": "TP.HPBITABLO4.18",
    "Yurt Dışı Yerleşikler - Diğer": "TP.HPBITABLO4.19",
    "Yurt Dışı Yerleşikler - Altın": "TP.HPBITABLO4.20",
    "Yurt Dışı Yerleşik Bankalar": "TP.HPBITABLO4.21",
}


# =========================================================
# YP PARİTE HARİÇ DEĞİŞİM VE PARİTE ETKİSİ SERİLERİ
# =========================================================

YP_CHANGE_SERIES = {
    "Parite Hariç - Yurt İçi Yerleşikler": "TP.HPBITABLO5.1",
    "Parite Hariç - Gerçek Kişiler": "TP.HPBITABLO5.2",
    "Parite Hariç - Gerçek Kişiler USD": "TP.HPBITABLO5.3",
    "Parite Hariç - Gerçek Kişiler EUR": "TP.HPBITABLO5.4",
    "Parite Hariç - Gerçek Kişiler Diğer": "TP.HPBITABLO5.5",
    "Parite Hariç - Gerçek Kişiler Altın": "TP.HPBITABLO5.6",
    "Parite Hariç - Tüzel Kişiler": "TP.HPBITABLO5.7",
    "Parite Hariç - Tüzel Kişiler USD": "TP.HPBITABLO5.8",
    "Parite Hariç - Tüzel Kişiler EUR": "TP.HPBITABLO5.9",
    "Parite Hariç - Tüzel Kişiler Diğer": "TP.HPBITABLO5.10",
    "Parite Hariç - Tüzel Kişiler Altın": "TP.HPBITABLO5.11",
    "Parite Etkisi - Yurt İçi Yerleşikler": "TP.HPBITABLO5.12",
    "Parite Etkisi - Gerçek Kişiler": "TP.HPBITABLO5.13",
    "Parite Etkisi - Gerçek Kişiler USD": "TP.HPBITABLO5.14",
    "Parite Etkisi - Gerçek Kişiler EUR": "TP.HPBITABLO5.15",
    "Parite Etkisi - Gerçek Kişiler Diğer": "TP.HPBITABLO5.16",
    "Parite Etkisi - Gerçek Kişiler Altın": "TP.HPBITABLO5.17",
    "Parite Etkisi - Tüzel Kişiler": "TP.HPBITABLO5.18",
    "Parite Etkisi - Tüzel Kişiler USD": "TP.HPBITABLO5.19",
    "Parite Etkisi - Tüzel Kişiler EUR": "TP.HPBITABLO5.20",
    "Parite Etkisi - Tüzel Kişiler Diğer": "TP.HPBITABLO5.21",
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
# KIRILIMLAR VE GÖSTERİM BİRİMLERİ
# =========================================================

BREAKDOWN = {
    "USD": {
        "individual_level": "Gerçek Kişiler - USD",
        "corporate_level": "Tüzel Kişiler - USD",
        "individual_adjusted": "Parite Hariç - Gerçek Kişiler USD",
        "corporate_adjusted": "Parite Hariç - Tüzel Kişiler USD",
        "individual_parity": "Parite Etkisi - Gerçek Kişiler USD",
        "corporate_parity": "Parite Etkisi - Tüzel Kişiler USD",
        "unit": "Milyon ABD doları",
    },
    "EUR": {
        "individual_level": "Gerçek Kişiler - EUR",
        "corporate_level": "Tüzel Kişiler - EUR",
        "individual_adjusted": "Parite Hariç - Gerçek Kişiler EUR",
        "corporate_adjusted": "Parite Hariç - Tüzel Kişiler EUR",
        "individual_parity": "Parite Etkisi - Gerçek Kişiler EUR",
        "corporate_parity": "Parite Etkisi - Tüzel Kişiler EUR",
        "unit": "Milyon euro",
    },
    "Diğer Döviz": {
        "individual_level": "Gerçek Kişiler - Diğer",
        "corporate_level": "Tüzel Kişiler - Diğer",
        "individual_adjusted": "Parite Hariç - Gerçek Kişiler Diğer",
        "corporate_adjusted": "Parite Hariç - Tüzel Kişiler Diğer",
        "individual_parity": "Parite Etkisi - Gerçek Kişiler Diğer",
        "corporate_parity": "Parite Etkisi - Tüzel Kişiler Diğer",
        "unit": "Milyon ABD doları karşılığı",
    },
    "Altın": {
        "individual_level": "Gerçek Kişiler - Altın",
        "corporate_level": "Tüzel Kişiler - Altın",
        "individual_adjusted": "Parite Hariç - Gerçek Kişiler Altın",
        "corporate_adjusted": "Parite Hariç - Tüzel Kişiler Altın",
        "individual_parity": "Parite Etkisi - Gerçek Kişiler Altın",
        "corporate_parity": "Parite Etkisi - Tüzel Kişiler Altın",
        "unit": "Altın mevduatı",
    },
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
    """
    Serileri 10'arlı gruplar halinde çeker.
    fetched_at, verinin gerçekten EVDS'den alındığı zamanı gösterir.
    Cache kullanıldığında çekim zamanı da cache ile birlikte korunur.
    """
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

        parsed = parse_evds_response(response.json(), chunk)
        frames.append(parsed)

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
    fetched_at = datetime.now().astimezone().strftime("%d.%m.%Y %H:%M:%S %Z")

    return result, fetched_at


def show_data_status(df, fetched_at):
    if df.empty:
        observation_date = "Veri yok"
    else:
        observation_date = df["Tarih"].max().strftime("%d.%m.%Y")

    st.caption(
        f"**Son veri çekimi:** {fetched_at}  |  "
        f"**Son gözlem tarihi:** {observation_date}  |  "
        "Veriler 1 saat önbellekte tutulur."
    )


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


def latest_value(df, column):
    if column not in df.columns or df.empty:
        return float("nan")
    return df.iloc[-1][column]


def format_value(value, unit="", decimals=2):
    if pd.isna(value):
        return "Veri yok"
    return f"{value:+,.{decimals}f} {unit}".strip()


def latest_difference(df, column, periods=1):
    if column not in df.columns or len(df) <= periods:
        return float("nan")
    return df[column].iloc[-1] - df[column].iloc[-1 - periods]


def rename_tl_csv_columns(df):
    rename_map = {}

    for name in TL_SERIES:
        if name in df.columns:
            rename_map[name] = f"{name} (Trilyon TL)"

    amount_columns = {
        "Haftalık Değişim": "Haftalık Değişim (Milyar TL)",
        "4 Haftalık Değişim": "4 Haftalık Değişim (Milyar TL)",
        "13 Haftalık Değişim": "13 Haftalık Değişim (Milyar TL)",
    }

    rename_map.update(amount_columns)

    percent_columns = [
        "Haftalık Değişim (%)",
        "4 Haftalık Değişim (%)",
        "13 Haftalık Değişim (%)",
    ]

    for col in percent_columns:
        if col in df.columns:
            rename_map[col] = col

    return df.rename(columns=rename_map)


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

    # EVDS TL serileri milyon TL varsayımıyla trilyon TL'ye çevrilir.
    tl_df[available_tl_columns] = tl_df[available_tl_columns] / 1_000_000

    total_col = "Toplam TL Mevduat"

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

    st.subheader("4 Haftalık Değişim Tablos")

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

    csv_df = rename_tl_csv_columns(tl_df.copy())

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
                (
                    "TL Mevduat Analiz Dashboard raporu ektedir.\n"
                    "Seviyeler trilyon TL, değişim tutarları milyar TL'dir."
                ),
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

if yp_df.empty or "Toplam YP Mevduat" not in yp_df.columns:
    st.error(
        "YP mevduat verileri bulunamadı. "
        "EVDS seri kodlarını ve dönen sütun adlarını kontrol et."
    )
    st.stop()

yp_df = yp_df.sort_values("Tarih").reset_index(drop=True)
yp_latest = yp_df.iloc[-1]
latest_date = yp_latest["Tarih"].strftime("%d.%m.%Y")

# ---------------------------------------------------------
# ÜST KARTLAR: MEVDUAT SEVİYELERİ
# ---------------------------------------------------------

st.subheader(f"Son Gözlem: {latest_date}")

c1, c2, c3, c4 = st.columns(4)

for col, name in zip(
    [c1, c2, c3, c4],
    [
        "Toplam YP Mevduat",
        "Yurt İçi Yerleşikler",
        "Gerçek Kişiler",
        "Tüzel Kişiler",
    ],
):
    value = latest_value(yp_df, name)
    col.metric(name, f"{value:,.2f}" if pd.notna(value) else "Veri yok")

st.caption(
    "YP seviye serileri EVDS'nin ilgili serilerinde yayımlanan birimlerle "
    "gösterilir. Kırılım grafiklerinde USD, EUR ve diğer döviz serileri "
    "ayrı ayrı incelenir."
)


# ---------------------------------------------------------
# HAFTALIK NOMİNAL DELTA VE PARİTE AYRIŞIMI
# ---------------------------------------------------------

st.subheader("Haftalık YP Mevduat Hareketi")

nominal_total = latest_difference(yp_df, "Toplam YP Mevduat")
nominal_domestic = latest_difference(yp_df, "Yurt İçi Yerleşikler")
nominal_individual = latest_difference(yp_df, "Gerçek Kişiler")
nominal_corporate = latest_difference(yp_df, "Tüzel Kişiler")

adjusted_domestic = latest_value(
    yp_df, "Parite Hariç - Yurt İçi Yerleşikler"
)
parity_domestic = latest_value(
    yp_df, "Parite Etkisi - Yurt İçi Yerleşikler"
)

d1, d2, d3, d4 = st.columns(4)

d1.metric(
    "Toplam YP — Haftalık nominal değişim",
    format_value(nominal_total),
)
d2.metric(
    "Yurt İçi Yerleşikler — Haftalık değişim",
    format_value(nominal_domestic),
)
d3.metric(
    "Gerçek Kişiler — Haftalık değişim",
    format_value(nominal_individual),
)
d4.metric(
    "Tüzel Kişiler — Haftalık değişim",
    format_value(nominal_corporate),
)

p1, p2, p3 = st.columns(3)

p1.metric(
    "Yurt İçi Yerleşikler — Nominal değişim",
    format_value(nominal_domestic),
)
p2.metric(
    "Parite hariç değişim",
    format_value(adjusted_domestic),
)
p3.metric(
    "Parite etkisi",
    format_value(parity_domestic),
)

st.caption(
    "Nominal değişim, seviye serisinin son iki gözlemi arasındaki farktır. "
    "Parite hariç değişim ve parite etkisi ilgili EVDS serilerinden alınır. "
    "Serilerin yayımlandığı birimler korunur."
)


# ---------------------------------------------------------
# GENEL YP MEVDUAT GELİŞİMİ
# ---------------------------------------------------------

st.subheader("YP Mevduat Gelişimi")

yp_level_columns = [
    "Toplam YP Mevduat",
    "Yurt İçi Yerleşikler",
    "Gerçek Kişiler",
    "Tüzel Kişiler",
]
yp_level_columns = [c for c in yp_level_columns if c in yp_df.columns]

yp_long = yp_df[["Tarih"] + yp_level_columns].melt(
    id_vars="Tarih",
    var_name="Mevduat Türü",
    value_name="Değer",
)

fig_yp = px.line(
    yp_long,
    x="Tarih",
    y="Değer",
    color="Mevduat Türü",
    title="YP Mevduat Seviyeleri",
    labels={"Tarih": "Tarih", "Değer": "Seri değeri"},
)
fig_yp.update_layout(hovermode="x unified")
st.plotly_chart(fig_yp, use_container_width=True)


# ---------------------------------------------------------
# USD / EUR / DİĞER DÖVİZ / ALTIN
# ---------------------------------------------------------

st.subheader("USD, EUR, Diğer Döviz ve Altın Kırılımı")

st.markdown(
    "Grafikler gerçek kişiler ve tüzel kişiler için ayrı gösterilir. "
    "Haftalık değişim tablolarında nominal değişim ile parite etkisinden "
    "arındırılmış değişim ve parite etkisi birlikte yer alır."
)

breakdown_rows = []
breakdown_level_figures = []
breakdown_delta_figures = []

for asset, config in BREAKDOWN.items():

    individual_level_col = config["individual_level"]
    corporate_level_col = config["corporate_level"]

    individual_adjusted_col = config["individual_adjusted"]
    corporate_adjusted_col = config["corporate_adjusted"]

    individual_parity_col = config["individual_parity"]
    corporate_parity_col = config["corporate_parity"]

    unit = config["unit"]

    # Her varlık için seviye grafiği
    level_columns = [
        c for c in [individual_level_col, corporate_level_col]
        if c in yp_df.columns
    ]

    if level_columns:
        level_long = yp_df[["Tarih"] + level_columns].melt(
            id_vars="Tarih",
            var_name="Mevduat Sahibi",
            value_name="Tutar",
        )

        level_long["Mevduat Sahibi"] = (
            level_long["Mevduat Sahibi"]
            .str.replace("Gerçek Kişiler - ", "", regex=False)
            .str.replace("Tüzel Kişiler - ", "", regex=False)
        )

        fig_level = px.line(
            level_long,
            x="Tarih",
            y="Tutar",
            color="Mevduat Sahibi",
            title=f"{asset} Mevduat Seviyesi",
            labels={
                "Tarih": "Tarih",
                "Tutar": unit,
                "Mevduat Sahibi": "Mevduat Sahibi",
            },
        )
        fig_level.update_yaxes(title_text=unit)
        fig_level.update_layout(hovermode="x unified")
        breakdown_level_figures.append((asset, fig_level))

    # Gerçek kişiler ve tüzel kişiler için haftalık delta
    for segment, level_col, adjusted_col, parity_col in [
        (
            "Gerçek Kişiler",
            individual_level_col,
            individual_adjusted_col,
            individual_parity_col,
        ),
        (
            "Tüzel Kişiler",
            corporate_level_col,
            corporate_adjusted_col,
            corporate_parity_col,
        ),
    ]:
        current_level = latest_value(yp_df, level_col)
        nominal_delta = latest_difference(yp_df, level_col)
        adjusted_delta = latest_value(yp_df, adjusted_col)
        parity_delta = latest_value(yp_df, parity_col)

        breakdown_rows.append({
            "Döviz / Varlık": asset,
            "Mevduat Sahibi": segment,
            f"Mevcut Seviye ({unit})": current_level,
            f"Nominal Haftalık Değişim ({unit})": nominal_delta,
            f"Parite Hariç Değişim ({unit})": adjusted_delta,
            f"Parite Etkisi ({unit})": parity_delta,
        })

    # Her varlık için nominal haftalık değişim grafiği
    delta_rows = []

    for segment, level_col in [
        ("Gerçek Kişiler", individual_level_col),
        ("Tüzel Kişiler", corporate_level_col),
    ]:
        if level_col not in yp_df.columns:
            continue

        temp = yp_df[["Tarih", level_col]].copy()
        temp["Haftalık Nominal Değişim"] = temp[level_col].diff()
        temp["Mevduat Sahibi"] = segment

        delta_rows.append(
            temp[["Tarih", "Haftalık Nominal Değişim", "Mevduat Sahibi"]]
        )

    if delta_rows:
        delta_long = pd.concat(delta_rows, ignore_index=True)

        fig_delta = px.bar(
            delta_long,
            x="Tarih",
            y="Haftalık Nominal Değişim",
            color="Mevduat Sahibi",
            barmode="group",
            title=f"{asset} — Haftalık Nominal Değişim",
            labels={
                "Tarih": "Tarih",
                "Haftalık Nominal Değişim": unit,
            },
        )
        fig_delta.update_yaxes(title_text=unit)
        breakdown_delta_figures.append((asset, fig_delta))


# Seviye grafikleri
for asset, fig in breakdown_level_figures:
    st.plotly_chart(fig, use_container_width=True)

# Nominal haftalık değişim grafikleri
st.subheader("Döviz ve Altın Kırılımlarında Haftalık Nominal Değişim")

for asset, fig in breakdown_delta_figures:
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------
# HAFTALIK DELTA TABLOSU
# ---------------------------------------------------------

st.subheader("Döviz ve Altın Kırılımlarında Haftalık Delta")

breakdown_df = pd.DataFrame(breakdown_rows)

st.dataframe(
    breakdown_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        col: st.column_config.NumberColumn(
            col,
            format="%+,.2f" if (
                "Değişim" in col or "Parite Etkisi" in col
            ) else "%,.2f",
        )
        for col in breakdown_df.columns
        if col not in ["Döviz / Varlık", "Mevduat Sahibi"]
    },
)

st.caption(
    "Nominal haftalık değişim seviye serisinin son iki gözlemi arasındaki "
    "farktır. Parite hariç değişim ve parite etkisi EVDS'nin ilgili "
    "değişim serilerinden alınır. EUR tutarları euro cinsinden gösterilir; "
    "diğer seriler kendi tanımlarındaki birimle gösterilir."
)


# ---------------------------------------------------------
# PARİTE ANALİZİ
# ---------------------------------------------------------

st.subheader("Parite Hariç Değişim ve Parite Etkisi")

change_options = [
    "Yurt İçi Yerleşikler",
    "Gerçek Kişiler",
    "Tüzel Kişiler",
    "Gerçek Kişiler USD",
    "Gerçek Kişiler EUR",
    "Gerçek Kişiler Diğer",
    "Gerçek Kişiler Altın",
    "Tüzel Kişiler USD",
    "Tüzel Kişiler EUR",
    "Tüzel Kişiler Diğer",
    "Tüzel Kişiler Altın",
]

change_lookup = {
    "Yurt İçi Yerleşikler": (
        "Parite Hariç - Yurt İçi Yerleşikler",
        "Parite Etkisi - Yurt İçi Yerleşikler",
    ),
    "Gerçek Kişiler": (
        "Parite Hariç - Gerçek Kişiler",
        "Parite Etkisi - Gerçek Kişiler",
    ),
    "Tüzel Kişiler": (
        "Parite Hariç - Tüzel Kişiler",
        "Parite Etkisi - Tüzel Kişiler",
    ),
    "Gerçek Kişiler USD": (
        "Parite Hariç - Gerçek Kişiler USD",
        "Parite Etkisi - Gerçek Kişiler USD",
    ),
    "Gerçek Kişiler EUR": (
        "Parite Hariç - Gerçek Kişiler EUR",
        "Parite Etkisi - Gerçek Kişiler EUR",
    ),
    "Gerçek Kişiler Diğer": (
        "Parite Hariç - Gerçek Kişiler Diğer",
        "Parite Etkisi - Gerçek Kişiler Diğer",
    ),
    "Gerçek Kişiler Altın": (
        "Parite Hariç - Gerçek Kişiler Altın",
        "Parite Etkisi - Gerçek Kişiler Altın",
    ),
    "Tüzel Kişiler USD": (
        "Parite Hariç - Tüzel Kişiler USD",
        "Parite Etkisi - Tüzel Kişiler USD",
    ),
    "Tüzel Kişiler EUR": (
        "Parite Hariç - Tüzel Kişiler EUR",
        "Parite Etkisi - Tüzel Kişiler EUR",
    ),
    "Tüzel Kişiler Diğer": (
        "Parite Hariç - Tüzel Kişiler Diğer",
        "Parite Etkisi - Tüzel Kişiler Diğer",
    ),
    "Tüzel Kişiler Altın": (
        "Parite Hariç - Tüzel Kişiler Altın",
        "Parite Etkisi - Tüzel Kişiler Altın",
    ),
}

selected_change = st.selectbox(
    "İncelenecek kırılım",
    change_options,
    key="yp_change_chart_selection",
)

adjusted_col, parity_col = change_lookup[selected_change]
chart_columns = [
    c for c in [adjusted_col, parity_col]
    if c in yp_df.columns
]

fig_change = None

if chart_columns:
    change_long = yp_df[["Tarih"] + chart_columns].melt(
        id_vars="Tarih",
        var_name="Değişim Türü",
        value_name="Değer",
    )

    fig_change = px.bar(
        change_long,
        x="Tarih",
        y="Değer",
        color="Değişim Türü",
        barmode="group",
        title=f"{selected_change}: Parite Hariç Değişim ve Parite Etkisi",
        labels={"Tarih": "Tarih", "Değer": "Seri değeri"},
    )
    fig_change.update_layout(hovermode="x unified")
    st.plotly_chart(fig_change, use_container_width=True)
else:
    st.warning("Seçilen kırılım için değişim serileri bulunamadı.")


# ---------------------------------------------------------
# YP VERİ TABLOSU VE CSV
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
            ("yp_mevduat_gelisimi.png", fig_to_png(fig_yp)),
        ]

        for asset, fig in breakdown_level_figures:
            attachments.append(
                (f"{asset.lower().replace(' ', '_')}_seviye.png", fig_to_png(fig))
            )

        for asset, fig in breakdown_delta_figures:
            attachments.append(
                (f"{asset.lower().replace(' ', '_')}_haftalik_delta.png", fig_to_png(fig))
            )

        if fig_change is not None:
            attachments.append(
                ("yp_parite_analizi.png", fig_to_png(fig_change))
            )

        send_email(
            "YP DTH Analiz Raporu",
            (
                "YP DTH Analiz Dashboard raporu ektedir.\n\n"
                "Raporda toplam mevduat seviyeleri, haftalık nominal değişimler, "
                "USD/EUR/diğer döviz/altın kırılımları ve parite etkisi "
                "analizleri yer almaktadır."
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
