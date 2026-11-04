    st.plotly_chart(fig, use_container_width=True)

# Üç değişim bileşenini birlikte gösteren grafikler
st.markdown("#### Nominal Değişim / Parite Hariç Değişim / Parite Etkisi")
for asset, fig in comparison_figures:
    st.plotly_chart(fig, use_container_width=True)

# Son gözlemin sayısal özeti
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
        "Nominal Değişim": st.column_config.NumberColumn(
            "Nominal Değişim",
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
    "Nominal değişim, ilgili mevduat seviyesi serisinin son iki gözlemi "
    "arasındaki farktır. Parite hariç değişim ve parite etkisi, ilgili "
    "TCMB EVDS değişim serilerinin son gözleminden alınır. Farklı serilerin "
    "ölçü birimleri aynı olmayabileceğinden tutarlar kendi seri tanımları "
    "çerçevesinde değerlendirilmelidir."
)


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

        for asset, fig in comparison_figures:
            attachments.append(
                (
                    f"{asset.lower().replace(' ', '_')}_parite_karsilastirma.png",
                    fig_to_png(fig),
                )
            )

        send_email(
            "YP DTH Analiz Raporu",
            (
                "YP DTH Analiz Dashboard raporu ektedir.\n\n"
                "Raporda toplam YP mevduat, gerçek kişiler, tüzel kişiler, "
                "USD/EUR/diğer döviz/altın seviyeleri ile gerçek ve tüzel kişiler için "
                "nominal değişim, parite hariç değişim ve parite etkisi "
                "karşılaştırmaları yer almaktadır."
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
