
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
# YP DTH SERİLERİ
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
            rename_map[
                normalized_columns[normalized_code]
            ] = display_name

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
    Serileri en fazla 10'arlı gruplar halinde alır.
    Dönen zaman damgası, önbelleğe alınan verinin son çekilme
    zamanını gösterir.
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

        parsed = parse_evds_response(
            response.json(),
            chunk,
        )
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

    # Bu değer cache'e kaydedilir. Cache'den tekrar okunduğunda
    # son gerçek çekim zamanı korunur.
    fetched_at = datetime.now().astimezone().isoformat(timespec="seconds")

    return result, fetched_at


def show_data_status(df, fetched_at):
    observation_date = (
        df["Tarih"].max().strftime("%d.%m.%Y")
        if not df.empty
        else "Veri yok"
    )

    st.caption(
        f"Son gözlem tarihi: **{observation_date}**  |  "
        f"Verinin son çekildiği zaman: **{fetched_at}**  |  "
        "Önbellek süresi: 1 saat"
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


def metric_value(value, unit="", decimals=2):
    if pd.isna(value):
        return "Veri yok"
    return f"{value:+,.{decimals}f} {unit}".strip()


def latest_value(df, column):
    if column not in df.columns or df.empty:
        return None
    return df.iloc[-1][column]


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

    if "Toplam TL Mevduat" not in available_tl_columns:
        st.error(
            "Toplam TL Mevduat serisi bulunamadı. "
            "EVDS sütun adlarını ve seri kodlarını kontrol et."
        )
        st.stop()

    if tl_df.empty:
        st.warning("Seçilen tarih aralığında veri bulunamadı.")
        st.stop()

    # EVDS seviyelerinin milyon TL cinsinden olduğu varsayılır.
    # Milyon TL -> trilyon TL.
    tl_value_columns = available_tl_columns
    tl_df[tl_value_columns] = tl_df[tl_value_columns] / 1_000_000

    total_col = "Toplam TL Mevduat"

    # Seviyeler trilyon TL, tutar değişimleri milyar TL.
    tl_df["Haftalık Değişim"] = tl_df[total_col].diff() * 1000
    tl_df["Haftalık Değişim (%)"] = tl_df[total_col].pct_change() * 100

    tl_df["4 Haftalık Değişim"] = (
        tl_df[total_col] - tl_df[total_col].shift(4)
    ) * 1000
    tl_df["4 Haftalık Değişim (%)"] = tl_df[total_col].pct_change(4) * 100

    tl_df["13 Haftalık Değişim"] = (
        tl_df[total_col] - tl_df[total_col].shift(13)
    ) * 1000
    tl_df["13 Haftalık Değişim (%)"] = tl_df[total_col].pct_change(13) * 100

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
        "Seviye verileri trilyon TL, değişim tutarları milyar TL, "
        "oranlar yüzde olarak gösterilir."
    )

    # Toplam seviye grafiği
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

    # Mevduat türlerine göre seviye grafiği
    person_columns = [
        "Gerçek Kişiler",
        "Ticari Kuruluşlar",
        "Resmî Kuruluşlar",
        "Kâr Amacı Olmayan Kuruluşlar",
        "Banka Dışı Finansal Kuruluşlar",
    ]
    person_columns = [c for c in person_columns if c in tl_df.columns]

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

    # Vadeli / vadesiz
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

    # Haftalık değişim grafiği
    fig_weekly = px.bar(
        tl_df,
        x="Tarih",
        y="Haftalık Değişim",
        title="Toplam TL Mevduatta Haftalık Değişim",
        labels={"Tarih": "Tarih", "Haftalık Değişim": "Milyar TL"},
    )
    fig_weekly.update_yaxes(title_text="Milyar TL")
    st.plotly_chart(fig_weekly, use_container_width=True)

    # Değişim tabloları
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

    # CSV: seviyeler trilyon TL, değişimler milyar TL
    st.subheader("Veri İndirme")
    csv_df = tl_df.copy().rename(columns={
        total_col: "Toplam TL Mevduat (Trilyon TL)",
        "Haftalık Değişim": "Haftalık Değişim (Milyar TL)",
        "4 Haftalık Değişim": "4 Haftalık Değişim (Milyar TL)",
        "13 Haftalık Değişim": "13 Haftalık Değişim (Milyar TL)",
    })

    st.download_button(
        "TL Mevduat CSV İndir",
        data=csv_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="tl_mevduat_analiz.csv",
        mime="text/csv",
    )

    # E-posta
    st.subheader("Rapor Gönderimi")
    if st.button("TL Mevduat Raporunu E-posta ile Gönder"):
        try:
            attachments = [
                ("toplam_tl_mevduat.png", fig_to_png(fig_total)),
                ("haftalik_degisim.png", fig_to_png(fig_weekly)),
            ]

            if person_columns:
                attachments.append(
                    ("mevduat_turleri.png", fig_to_png(fig_person))
                )
            if maturity_columns:
                attachments.append(
                    ("vadeli_vadesiz.png", fig_to_png(fig_maturity))
                )

            send_email(
                "TL Mevduat Analiz Raporu",
                "TL Mevduat Analiz Dashboard raporu ektedir.\n"
                "Seviyeler trilyon TL, değişim tutarları milyar TL'dir.",
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
        "YP mevduat verileri bulunamadı. EVDS seri kodlarını ve "
        "dönen sütun adlarını kontrol et."
    )
    st.stop()

yp_df = yp_df.sort_values("Tarih").reset_index(drop=True)
yp_latest = yp_df.iloc[-1]

if len(yp_df) >= 2:
    yp_previous = yp_df.iloc[-2]
    nominal_change = (
        yp_latest["Toplam YP Mevduat"]
        - yp_previous["Toplam YP Mevduat"]
    )
else:
    nominal_change = float("nan")

adjusted_change = latest_value(
    yp_df,
    "Parite Hariç - Yurt İçi Yerleşikler",
)
parity_effect = latest_value(
    yp_df,
    "Parite Etkisi - Yurt İçi Yerleşikler",
)

# Üst kartlar: seviyeden önce haftalık hareket
st.subheader("Haftalık YP Mevduat Hareketi")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Nominal Haftalık Değişim",
    metric_value(nominal_change, "EVDS birimi"),
)
c2.metric(
    "Parite Hariç Değişim",
    metric_value(adjusted_change, "EVDS birimi"),
)
c3.metric(
    "Parite Etkisi",
    metric_value(parity_effect, "EVDS birimi"),
)
c4.metric(
    "Toplam YP Mevduat",
    f"{yp_latest['Toplam YP Mevduat']:,.2f}",
)

st.caption(
    "Nominal değişim, toplam mevduat seviyesinin son iki gözlem arasındaki "
    "farkıdır. Parite hariç değişim ve parite etkisi EVDS serilerinden "
    "doğrudan alınır. Birimler EVDS serisinin kendi birimidir."
)

# Seviye kartları
st.subheader("YP Mevduat Seviyeleri")

level_columns = [
    "Yurt İçi Yerleşikler",
    "Gerçek Kişiler",
    "Tüzel Kişiler",
]

level_cols = st.columns(len(level_columns))

for col, name in zip(level_cols, level_columns):
    if name in yp_df.columns:
        col.metric(name, f"{yp_latest[name]:,.2f}")

# Nominal seviye grafiği
st.subheader("YP Mevduat Gelişimi")

yp_level_columns = [
    "Toplam YP Mevduat",
    "Yurt İçi Yerleşikler",
    "Gerçek Kişiler",
    "Tüzel Kişiler",
]
yp_level_columns = [
    c for c in yp_level_columns if c in yp_df.columns
]

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
    title="YP Mevduat Gelişimi",
    labels={"Tarih": "Tarih", "Değer": "EVDS birimi"},
)
fig_yp.update_layout(hovermode="x unified")
st.plotly_chart(fig_yp, use_container_width=True)

# USD / EUR / diğer / altın kırılımı
st.subheader("USD, EUR, Diğer Döviz ve Altın Kırılımı")

breakdown_map = {
    "USD": (
        "Gerçek Kişiler - USD",
        "Tüzel Kişiler - USD",
        "Parite Hariç - Gerçek Kişiler USD",
        "Parite Hariç - Tüzel Kişiler USD",
        "Parite Etkisi - Gerçek Kişiler USD",
        "Parite Etkisi - Tüzel Kişiler USD",
    ),
    "EUR": (
        "Gerçek Kişiler - EUR",
        "Tüzel Kişiler - EUR",
        "Parite Hariç - Gerçek Kişiler EUR",
        "Parite Hariç - Tüzel Kişiler EUR",
        "Parite Etkisi - Gerçek Kişiler EUR",
        "Parite Etkisi - Tüzel Kişiler EUR",
    ),
    "Diğer Döviz": (
        "Gerçek Kişiler - Diğer",
        "Tüzel Kişiler - Diğer",
        "Parite Hariç - Gerçek Kişiler Diğer",
        "Parite Hariç - Tüzel Kişiler Diğer",
        "Parite Etkisi - Gerçek Kişiler Diğer",
        "Parite Etkisi - Tüzel Kişiler Diğer",
    ),
    "Altın": (
        "Gerçek Kişiler - Altın",
        "Tüzel Kişiler - Altın",
        "Parite Hariç - Gerçek Kişiler Altın",
        "Parite Hariç - Tüzel Kişiler Altın",
        "Parite Etkisi - Gerçek Kişiler Altın",
        "Parite Etkisi - Tüzel Kişiler Altın",
    ),
}

breakdown_rows = []

for currency, columns in breakdown_map.items():
    (
        individual_level,
        corporate_level,
        individual_adjusted,
        corporate_adjusted,
        individual_parity,
        corporate_parity,
    ) = columns

    for segment, level_col, adj_col, parity_col in [
        (
            "Gerçek Kişiler",
            individual_level,
            individual_adjusted,
            individual_parity,
        ),
        (
            "Tüzel Kişiler",
            corporate_level,
            corporate_adjusted,
            corporate_parity,
        ),
    ]:
        level = latest_value(yp_df, level_col)

        if level_col in yp_df.columns and len(yp_df) >= 2:
            nominal = (
                yp_df.iloc[-1][level_col]
                - yp_df.iloc[-2][level_col]
            )
        else:
            nominal = float("nan")

        adjusted = latest_value(yp_df, adj_col)
        parity = latest_value(yp_df, parity_col)

        breakdown_rows.append({
            "Döviz / Varlık": currency,
            "Mevduat Sahibi": segment,
            "Mevcut Seviye": level,
            "Nominal Haftalık Değişim": nominal,
            "Parite Hariç Değişim": adjusted,
            "Parite Etkisi": parity,
        })

breakdown_df = pd.DataFrame(breakdown_rows)

st.dataframe(
    breakdown_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Mevcut Seviye": st.column_config.NumberColumn(
            "Mevcut Seviye (EVDS birimi)",
            format="%,.2f",
        ),
        "Nominal Haftalık Değişim": st.column_config.NumberColumn(
            "Nominal Haftalık Değişim (EVDS birimi)",
            format="%+,.2f",
        ),
        "Parite Hariç Değişim": st.column_config.NumberColumn(
            "Parite Hariç Değişim (EVDS birimi)",
            format="%+,.2f",
        ),
        "Parite Etkisi": st.column_config.NumberColumn(
            "Parite Etkisi (EVDS birimi)",
            format="%+,.2f",
        ),
    },
)

# Parite hariç ve parite etkisi serilerini zaman içinde göster
st.subheader("Parite Hariç Değişim ve Parite Etkisi")

change_chart_options = [
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

selected_change = st.selectbox(
    "İncelenecek kırılım",
    change_chart_options,
    key="yp_change_chart_selection",
)

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

adjusted_col, parity_col = change_lookup[selected_change]
chart_columns = [
    c for c in [adjusted_col, parity_col]
    if c in yp_df.columns
]

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
        labels={"Tarih": "Tarih", "Değer": "EVDS birimi"},
    )
    st.plotly_chart(fig_change, use_container_width=True)
else:
    st.warning("Seçilen kırılım için değişim serileri bulunamadı.")

# YP veri tablosu ve CSV
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

# E-posta raporu
st.subheader("Rapor Gönderimi")

if st.button("YP DTH Raporunu E-posta ile Gönder"):
    try:
        attachments = [
            ("yp_mevduat_gelisimi.png", fig_to_png(fig_yp)),
        ]

        if chart_columns:
            attachments.append(
                ("yp_parite_analizi.png", fig_to_png(fig_change))
            )

        send_email(
            "YP DTH Analiz Raporu",
            (
                "YP DTH Analiz Dashboard raporu ektedir.\n\n"
                "Raporda nominal mevduat değişimleri, parite etkisinden "
                "arındırılmış değişimler ve USD/EUR/diğer/altın kırılımları "
                "yer almaktadır."
            ),
            attachments,
        )

        st.success("E-posta başarıyla gönderildi.")

    except Exception as e:
        st.error(f"E-posta gönderilemedi: {e}")
