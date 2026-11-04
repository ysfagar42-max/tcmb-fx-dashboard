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
