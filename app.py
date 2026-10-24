
import io
import smtplib
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import matplotlib.pyplot as plt

from email.message import EmailMessage
from datetime import date, timedelta


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
# GİZLİ BİLGİLER
# Streamlit Cloud > Settings > Secrets bölümünden okunur.
# =========================================================

try:
    EVDS_API_KEY = st.secrets["evds_api_key"]
    GMAIL_ADDRESS = st.secrets["gmail_address"]
    GMAIL_APP_PASSWORD = st.secrets["gmail_app_password"]
except Exception:
    st.error(
        "Gerekli Secrets bilgileri bulunamadı. "
        "Streamlit ayarlarından evds_api_key, gmail_address "
        "ve gmail_app_password tanımlarını kontrol et."
    )
    st.stop()


EMAIL_RECIPIENT = "ysfagar42@gmail.com"


# =========================================================
# EVDS SERİLERİ
# =========================================================

YP_SERIES = {
    "Toplam YP Mevduat": "TP.HPBITABLO4.1",
    "Yurt İçi Yerleşikler": "TP.HPBITABLO4.2",
    "Gerçek Kişiler": "TP.HPBITABLO4.3",
    "Tüzel Kişiler": "TP.HPBITABLO4.8",
    "Gerçek Kişiler - Parite Etkisinden Arındırılmış Değişim": "TP.HPBITABLO5.2",
    "Tüzel Kişiler - Parite Etkisinden Arındırılmış Değişim": "TP.HPBITABLO5.7",
}

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
    """EVDS sütun adlarını karşılaştırmayı kolaylaştırır."""
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
    """EVDS yanıtını tarih ve seri sütunlarından oluşan DataFrame'e çevirir."""
    if isinstance(raw, dict):
        if "items" in raw:
            raw = raw["items"]
        elif "data" in raw:
            raw = raw["data"]
        else:
            raise ValueError(
                f"EVDS beklenmeyen bir yanıt döndürdü: {str(raw)[:300]}"
            )

    df = pd.DataFrame(raw)

    if df.empty:
        raise ValueError("EVDS seçilen tarih aralığı için veri döndürmedi.")

    date_candidates = [
        c for c in df.columns
        if normalize_column(c) in ("tarih", "date")
    ]

    if not date_candidates:
        date_candidates = [df.columns[0]]

    date_col = date_candidates[0]
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
            actual_column = normalized_columns[normalized_code]
            rename_map[actual_column] = display_name

    df = df.rename(columns=rename_map)

    for display_name in series_dict:
        if display_name in df.columns:
            df[display_name] = pd.to_numeric(
                df[display_name]
                .astype(str)
                .str.replace(",", ".", regex=False),
                errors="coerce",
            )

    df = (
        df.dropna(subset=["Tarih"])
        .sort_values("Tarih")
        .drop_duplicates(subset=["Tarih"], keep="last")
        .reset_index(drop=True)
    )

    return df


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_evds_data(start_date, end_date, series_items):
    """EVDS'den serileri indirir ve önbelleğe alır."""
    series_dict = dict(series_items)
    series_string = "-".join(series_dict.values())

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

    return parse_evds_response(
        response.json(),
        series_dict,
    )


def fig_to_png(fig):
    """Plotly grafiğini PNG olarak üretir."""
    return fig.to_image(
        format="png",
        width=1400,
        height=700,
        scale=2,
    )


def send_email(subject, body, attachments):
    """E-posta ve PNG eklerini gönderir."""
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


def show_date_filters():
    """Tarih filtrelerini gösterir."""
    today = date.today()
    default_start = today - timedelta(days=365)

    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input(
            "Başlangıç tarihi",
            value=default_start,
            max_value=today,
            key="start_date_filter",
        )

    with col2:
        end_date = st.date_input(
            "Bitiş tarihi",
            value=today,
            max_value=today,
            key="end_date_filter",
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

    start_date, end_date = show_date_filters()

    with st.spinner("TL mevduat verileri getiriliyor..."):
        try:
            tl_df = fetch_evds_data(
                start_date,
                end_date,
                tuple(TL_SERIES.items()),
            )
        except Exception as e:
            st.error(f"TL verileri alınamadı: {e}")
            st.stop()

    available_tl_columns = [
        name for name in TL_SERIES
        if name in tl_df.columns
    ]

    if "Toplam TL Mevduat" not in available_tl_columns:
        st.error(
            "Toplam TL Mevduat serisi bulunamadı. "
            "EVDS seri kodlarını ve dönen sütun adlarını kontrol et."
        )
        st.stop()

    if tl_df.empty:
        st.warning("Seçilen tarih aralığında veri bulunamadı.")
        st.stop()

    # EVDS seviye verilerinin milyon TL olduğu varsayılır.
    # Milyon TL -> trilyon TL dönüşümü.
    tl_value_columns = available_tl_columns

    tl_df[tl_value_columns] = (
        tl_df[tl_value_columns] / 1_000_000
    )

    total_col = "Toplam TL Mevduat"

    # Seviye verileri trilyon TL.
    # Değişimler milyar TL olarak hesaplanır.
    tl_df["Haftalık Değişim"] = (
        tl_df[total_col].diff() * 1000
    )
    tl_df["Haftalık Değişim (%)"] = (
        tl_df[total_col].pct_change() * 100
    )

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

    previous_tl = (
        tl_df.iloc[-2]
        if len(tl_df) > 1
        else None
    )

    # -----------------------------------------------------
    # ÖZET KARTLAR
    # -----------------------------------------------------

    st.subheader("Genel Görünüm")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Toplam TL Mevduat",
        f"{latest_tl[total_col]:,.2f} trilyon TL",
    )

    c2.metric(
        "Yurt İçi Yerleşikler",
        (
            f"{latest_tl['Yurt İçi Yerleşikler']:,.2f} trilyon TL"
            if "Yurt İçi Yerleşikler" in tl_df.columns
            else "Veri yok"
        ),
    )

    c3.metric(
        "Haftalık Değişim",
        (
            f"{latest_tl['Haftalık Değişim']:+,.1f} milyar TL"
            if pd.notna(latest_tl["Haftalık Değişim"])
            else "Veri yok"
        ),
        (
            f"{latest_tl['Haftalık Değişim (%)']:+.2f}%"
            if pd.notna(latest_tl["Haftalık Değişim (%)"])
            else None
        ),
    )

    c4.metric(
        "4 Haftalık Değişim",
        (
            f"{latest_tl['4 Haftalık Değişim']:+,.1f} milyar TL"
            if pd.notna(latest_tl["4 Haftalık Değişim"])
            else "Veri yok"
        ),
        (
            f"{latest_tl['4 Haftalık Değişim (%)']:+.2f}%"
            if pd.notna(latest_tl["4 Haftalık Değişim (%)"])
            else None
        ),
    )

    st.caption(
        "Mevduat seviyeleri trilyon TL, tutar değişimleri milyar TL "
        "ve değişim oranları yüzde olarak gösterilir."
    )

    # -----------------------------------------------------
    # TOPLAM TL MEVDUAT GRAFİĞİ
    # -----------------------------------------------------

    st.subheader("Toplam TL Mevduat")

    fig_total = px.line(
        tl_df,
        x="Tarih",
        y=total_col,
        title="Toplam TL Mevduat",
        labels={
            "Tarih": "Tarih",
            total_col: "Trilyon TL",
        },
    )

    fig_total.update_yaxes(title_text="Trilyon TL")
    fig_total.update_layout(hovermode="x unified")

    st.plotly_chart(
        fig_total,
        use_container_width=True,
    )

    # -----------------------------------------------------
    # MEVDUAT TÜRÜ GRAFİKLERİ
    # -----------------------------------------------------

    st.subheader("Mevduat Türlerine Göre Dağılım")

    person_columns = [
        "Gerçek Kişiler",
        "Ticari Kuruluşlar",
        "Resmî Kuruluşlar",
        "Kâr Amacı Olmayan Kuruluşlar",
        "Banka Dışı Finansal Kuruluşlar",
    ]

    person_columns = [
        c for c in person_columns
        if c in tl_df.columns
    ]

    if person_columns:
        person_long = tl_df[
            ["Tarih"] + person_columns
        ].melt(
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
            labels={
                "Tarih": "Tarih",
                "Tutar": "Trilyon TL",
            },
        )

        fig_person.update_yaxes(title_text="Trilyon TL")
        fig_person.update_layout(hovermode="x unified")

        st.plotly_chart(
            fig_person,
            use_container_width=True,
        )

    # -----------------------------------------------------
    # VADELİ / VADESİZ GRAFİĞİ
    # -----------------------------------------------------

    st.subheader("Vadeli ve Vadesiz Mevduat")

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

    maturity_columns = [
        c for c in maturity_columns
        if c in tl_df.columns
    ]

    if maturity_columns:
        maturity_long = tl_df[
            ["Tarih"] + maturity_columns
        ].melt(
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
            labels={
                "Tarih": "Tarih",
                "Tutar": "Trilyon TL",
            },
        )

        fig_maturity.update_yaxes(title_text="Trilyon TL")
        fig_maturity.update_layout(hovermode="x unified")

        st.plotly_chart(
            fig_maturity,
            use_container_width=True,
        )

    # -----------------------------------------------------
    # HAFTALIK DEĞİŞİM GRAFİĞİ
    # -----------------------------------------------------

    st.subheader("Haftalık Değişim")

    fig_weekly = px.bar(
        tl_df,
        x="Tarih",
        y="Haftalık Değişim",
        title="Toplam TL Mevduatta Haftalık Değişim",
        labels={
            "Tarih": "Tarih",
            "Haftalık Değişim": "Milyar TL",
        },
    )

    fig_weekly.update_yaxes(title_text="Milyar TL")
    st.plotly_chart(
        fig_weekly,
        use_container_width=True,
    )

    # -----------------------------------------------------
    # DEĞİŞİM TABLOLARI
    # -----------------------------------------------------

    st.subheader("Haftalık Değişim Tablosu")

    weekly_table = tl_df[
        [
            "Tarih",
            total_col,
            "Haftalık Değişim",
            "Haftalık Değişim (%)",
        ]
    ].copy()

    weekly_table = weekly_table.rename(
        columns={
            total_col: "Toplam TL Mevduat (Trilyon TL)",
            "Haftalık Değişim": "Haftalık Değişim (Milyar TL)",
            "Haftalık Değişim (%)": "Haftalık Değişim (%)",
        }
    )

    st.dataframe(
        weekly_table.sort_values(
            "Tarih",
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("4 Haftalık Değişim Tablosu")

    four_week_table = tl_df[
        [
            "Tarih",
            total_col,
            "4 Haftalık Değişim",
            "4 Haftalık Değişim (%)",
        ]
    ].copy()

    four_week_table = four_week_table.rename(
        columns={
            total_col: "Toplam TL Mevduat (Trilyon TL)",
            "4 Haftalık Değişim": "4 Haftalık Değişim (Milyar TL)",
            "4 Haftalık Değişim (%)": "4 Haftalık Değişim (%)",
        }
    )

    st.dataframe(
        four_week_table.sort_values(
            "Tarih",
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("13 Haftalık Değişim Tablosu")

    thirteen_week_table = tl_df[
        [
            "Tarih",
            total_col,
            "13 Haftalık Değişim",
            "13 Haftalık Değişim (%)",
        ]
    ].copy()

    thirteen_week_table = thirteen_week_table.rename(
        columns={
            total_col: "Toplam TL Mevduat (Trilyon TL)",
            "13 Haftalık Değişim": "13 Haftalık Değişim (Milyar TL)",
            "13 Haftalık Değişim (%)": "13 Haftalık Değişim (%)",
        }
    )

    st.dataframe(
        thirteen_week_table.sort_values(
            "Tarih",
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
    )

    # -----------------------------------------------------
    # CSV İNDİRME
    # Seviye sütunları trilyon TL, değişim tutarları milyar TL.
    # -----------------------------------------------------

    st.subheader("Veri İndirme")

    csv_df = tl_df.copy()

    csv_rename = {
        total_col: "Toplam TL Mevduat (Trilyon TL)",
        "Haftalık Değişim": "Haftalık Değişim (Milyar TL)",
        "4 Haftalık Değişim": "4 Haftalık Değişim (Milyar TL)",
        "13 Haftalık Değişim": "13 Haftalık Değişim (Milyar TL)",
    }

    csv_df = csv_df.rename(columns=csv_rename)

    csv_data = csv_df.to_csv(
        index=False,
    ).encode("utf-8-sig")

    st.download_button(
        label="TL Mevduat CSV İndir",
        data=csv_data,
        file_name="tl_mevduat_analiz.csv",
        mime="text/csv",
    )

    # -----------------------------------------------------
    # E-POSTA GÖNDERİMİ
    # -----------------------------------------------------

    st.subheader("Rapor Gönderimi")

    if st.button("TL Mevduat Raporunu E-posta ile Gönder"):
        try:
            attachments = [
                (
                    "toplam_tl_mevduat.png",
                    fig_to_png(fig_total),
                )
            ]

            if person_columns:
                attachments.append(
                    (
                        "mevduat_turleri.png",
                        fig_to_png(fig_person),
                    )
                )

            if maturity_columns:
                attachments.append(
                    (
                        "vadeli_vadesiz.png",
                        fig_to_png(fig_maturity),
                    )
                )

            attachments.append(
                (
                    "haftalik_degisim.png",
                    fig_to_png(fig_weekly),
                )
            )

            send_email(
                subject="TL Mevduat Analiz Raporu",
                body=(
                    "TL Mevduat Analiz Dashboard raporu ektedir.\n\n"
                    "Mevduat seviyeleri trilyon TL, "
                    "değişim tutarları milyar TL olarak gösterilmiştir."
                ),
                attachments=attachments,
            )

            st.success("E-posta başarıyla gönderildi.")

        except Exception as e:
            st.error(
                "E-posta gönderilemedi. Gmail ayarlarını ve "
                f"gerekli paketleri kontrol et. Ayrıntı: {e}"
            )

    st.stop()


# =========================================================
# YP DTH PANELİ
# Mevcut YP panelinin işlevleri korunur.
# =========================================================

st.header("YP DTH Analizi")

start_date, end_date = show_date_filters()

with st.spinner("YP DTH verileri getiriliyor..."):
    try:
        yp_df = fetch_evds_data(
            start_date,
            end_date,
            tuple(YP_SERIES.items()),
        )
    except Exception as e:
        st.error(f"YP DTH verileri alınamadı: {e}")
        st.stop()

available_yp_columns = [
    name for name in YP_SERIES
    if name in yp_df.columns
]

if "Toplam YP Mevduat" not in available_yp_columns:
    st.error(
        "Toplam YP Mevduat serisi bulunamadı. "
        "EVDS seri kodlarını ve dönen sütun adlarını kontrol et."
    )
    st.stop()

if yp_df.empty:
    st.warning("Seçilen tarih aralığında veri bulunamadı.")
    st.stop()

yp_df = yp_df.sort_values("Tarih").reset_index(drop=True)

# EVDS serilerinin birimlerine göre gerekiyorsa burada dönüşüm yapılmalıdır.
# Bu bölümde mevcut YP verileri orijinal EVDS değerleriyle korunur.

yp_total_col = "Toplam YP Mevduat"

st.subheader("Genel Görünüm")

yp_latest = yp_df.iloc[-1]

yp_c1, yp_c2, yp_c3, yp_c4 = st.columns(4)

yp_c1.metric(
    "Toplam YP Mevduat",
    f"{yp_latest[yp_total_col]:,.2f}",
)

if "Yurt İçi Yerleşikler" in yp_df.columns:
    yp_c2.metric(
        "Yurt İçi Yerleşikler",
        f"{yp_latest['Yurt İçi Yerleşikler']:,.2f}",
    )

if "Gerçek Kişiler" in yp_df.columns:
    yp_c3.metric(
        "Gerçek Kişiler",
        f"{yp_latest['Gerçek Kişiler']:,.2f}",
    )

if "Tüzel Kişiler" in yp_df.columns:
    yp_c4.metric(
        "Tüzel Kişiler",
        f"{yp_latest['Tüzel Kişiler']:,.2f}",
    )

st.subheader("YP Mevduat Gelişimi")

yp_level_columns = [
    "Toplam YP Mevduat",
    "Yurt İçi Yerleşikler",
    "Gerçek Kişiler",
    "Tüzel Kişiler",
]

yp_level_columns = [
    c for c in yp_level_columns
    if c in yp_df.columns
]

yp_long = yp_df[
    ["Tarih"] + yp_level_columns
].melt(
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
    labels={
        "Tarih": "Tarih",
        "Değer": "EVDS değeri",
    },
)

fig_yp.update_layout(hovermode="x unified")

st.plotly_chart(
    fig_yp,
    use_container_width=True,
)

# ---------------------------------------------------------
# PARİTE ETKİSİNDEN ARINDIRILMIŞ DEĞİŞİMLER
# ---------------------------------------------------------

st.subheader("Parite Etkisinden Arındırılmış Değişim")

parity_columns = [
    "Gerçek Kişiler - Parite Etkisinden Arındırılmış Değişim",
    "Tüzel Kişiler - Parite Etkisinden Arındırılmış Değişim",
]

parity_columns = [
    c for c in parity_columns
    if c in yp_df.columns
]

if parity_columns:
    parity_long = yp_df[
        ["Tarih"] + parity_columns
    ].melt(
        id_vars="Tarih",
        var_name="Mevduat Türü",
        value_name="Değişim",
    )

    fig_parity = px.bar(
        parity_long,
        x="Tarih",
        y="Değişim",
        color="Mevduat Türü",
        barmode="group",
        title="Parite Etkisinden Arındırılmış Değişim",
        labels={
            "Tarih": "Tarih",
            "Değişim": "EVDS değeri",
        },
    )

    st.plotly_chart(
        fig_parity,
        use_container_width=True,
    )

# ---------------------------------------------------------
# YP TABLOSU VE CSV
# ---------------------------------------------------------

st.subheader("YP Mevduat Verileri")

st.dataframe(
    yp_df.sort_values("Tarih", ascending=False),
    use_container_width=True,
    hide_index=True,
)

yp_csv = yp_df.to_csv(
    index=False,
).encode("utf-8-sig")

st.download_button(
    label="YP DTH CSV İndir",
    data=yp_csv,
    file_name="yp_dth_analiz.csv",
    mime="text/csv",
)

# ---------------------------------------------------------
# YP E-POSTA RAPORU
# ---------------------------------------------------------

st.subheader("Rapor Gönderimi")

if st.button("YP DTH Raporunu E-posta ile Gönder"):
    try:
        yp_attachments = [
            (
                "yp_mevduat_gelisimi.png",
                fig_to_png(fig_yp),
            )
        ]

        if parity_columns:
            yp_attachments.append(
                (
                    "yp_parite_etkisinden_arindirilmis_degisim.png",
                    fig_to_png(fig_parity),
                )
            )

        send_email(
            subject="YP DTH Analiz Raporu",
            body=(
                "YP DTH Analiz Dashboard raporu ektedir.\n\n"
                "Veriler seçilen tarih aralığına göre hazırlanmıştır."
            ),
            attachments=yp_attachments,
        )

        st.success("E-posta başarıyla gönderildi.")

    except Exception as e:
        st.error(
            "E-posta gönderilemedi. Gmail ayarlarını ve "
            f"gerekli paketleri kontrol et. Ayrıntı: {e}"
        )
