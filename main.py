import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title="Stok ve Envanter Yönetimi / Inventory Management", layout="wide")

# SAĞ ÜST KÖŞE: DİL SEÇİMİ
col_bosluk, col_dil = st.columns([8, 2])
with col_dil:
    secilen_dil = st.selectbox("🌍 Dil / Language", ["Türkçe", "English"], index=0)

# Çeviri Fonksiyonu (Seçilen dile göre doğru metni döndürür)
def t(tr, en):
    return tr if secilen_dil == "Türkçe" else en

st.title(t("Çoklu Ürün Karar Destek ve Stok Planlama Sistemi", "Multi-Product Decision Support & Inventory Planning System"))
st.markdown("---")

# YAN MENÜ: VERİ YÜKLEME
st.sidebar.header(t("1. Veri Kaynağı", "1. Data Source"))
yuklenen_dosya = st.sidebar.file_uploader(t("Satış Geçmişi Yükle (CSV)", "Upload Sales History (CSV)"), type=["csv"])

if yuklenen_dosya is not None:
    df = pd.read_csv(yuklenen_dosya)
    st.sidebar.success(t("Veri başarıyla yüklendi.", "Data uploaded successfully."))
else:
    try:
        df = pd.read_csv('satis_verisi_1_aylik.csv')
        st.sidebar.info(t("Sistemde 1 aylık simülasyon verisi aktif.", "1-month simulation data is active."))
    except:
        st.error(t("Lütfen bir CSV dosyası yükleyin veya veri oluşturucu scripti çalıştırın.", "Please upload a CSV file or run the data generator script."))
        st.stop()

st.sidebar.markdown("---")

# YAN MENÜ: FİNANSAL PARAMETRELER
st.sidebar.header(t("2. Finansal Parametreler", "2. Financial Parameters"))
birim_urun_maliyeti = st.sidebar.number_input(t("Birim Ürün Maliyeti", "Unit Product Cost"), min_value=0.0, value=120.0, step=10.0)
birim_kar = st.sidebar.number_input(t("Birim Başına Net Kar", "Net Profit per Unit"), min_value=0.0, value=40.0, step=5.0)
elde_tutma_orani = st.sidebar.slider(t("Yıllık Stok Tutma Maliyet Oranı (%)", "Annual Inventory Holding Cost Rate (%)"), 0, 100, 20) / 100

# ABC ANALİZİ ALGORİTMASI 
abc_df = df.groupby('Urun_Adi')['Satis_Adedi'].sum().reset_index()
abc_df['Hacim'] = abc_df['Satis_Adedi'] * birim_urun_maliyeti
abc_df = abc_df.sort_values(by='Hacim', ascending=False)
abc_df['Kümülatif_Hacim'] = abc_df['Hacim'].cumsum()
abc_df['Kümülatif_Yüzde'] = abc_df['Kümülatif_Hacim'] / abc_df['Hacim'].sum()

def siniflandir(yuzde):
    if yuzde <= 0.80: return t('A Sınıfı (Yüksek Öncelik)', 'Class A (High Priority)')
    elif yuzde <= 0.95: return t('B Sınıfı (Orta Öncelik)', 'Class B (Medium Priority)')
    else: return t('C Sınıfı (Düşük Öncelik)', 'Class C (Low Priority)')

abc_df['ABC_Sinifi'] = abc_df['Kümülatif_Yüzde'].apply(siniflandir)
abc_dict = pd.Series(abc_df.ABC_Sinifi.values, index=abc_df.Urun_Adi).to_dict()

# YAN MENÜ: ÜRÜN SEÇİMİ VE RİSK YÖNETİMİ
st.sidebar.markdown("---")
st.sidebar.header(t("3. Planlama ve Risk Yönetimi", "3. Planning and Risk Management"))
urun_listesi = df['Urun_Adi'].unique()
secilen_urun = st.sidebar.selectbox(t("Analiz Edilecek Ürün:", "Product to Analyze:"), urun_listesi)

secilen_urun_sinifi = abc_dict.get(secilen_urun, "Bilinmiyor")
st.sidebar.markdown(t(f"**Sistem Notu:** Seçilen ürün **{secilen_urun_sinifi}** kategorisindedir.", f"**System Note:** Selected product is in the **{secilen_urun_sinifi}** category."))

hizmet_seviyeleri_tr = {"%90 (Agresif Düşük Stok)": 1.28, "%95 (Dengeli Standart)": 1.645, "%99 (Garantici Yüksek Stok)": 2.33}
hizmet_seviyeleri_en = {"90% (Aggressive Low Stock)": 1.28, "95% (Balanced Standard)": 1.645, "99% (Conservative High Stock)": 2.33}
hizmet_seviyeleri = hizmet_seviyeleri_tr if secilen_dil == "Türkçe" else hizmet_seviyeleri_en

secilen_hizmet_seviyesi = st.sidebar.selectbox(t("Müşteri Hizmet Seviyesi Hedefi:", "Target Customer Service Level:"), list(hizmet_seviyeleri.keys()), index=1)
Z = hizmet_seviyeleri[secilen_hizmet_seviyesi]

# SEÇİLEN ÜRÜN İÇİN HESAPLAMALAR
df_secilen = df[df['Urun_Adi'] == secilen_urun].reset_index(drop=True)

ortalama_satis = df_secilen['Satis_Adedi'].mean()
standart_sapma_satis = df_secilen['Satis_Adedi'].std()
tedarik_suresi = df_secilen['Tedarik_Suresi_Gun'].iloc[0]

emniyet_stoku = round(Z * standart_sapma_satis * np.sqrt(tedarik_suresi))
yeniden_siparis_noktasi = round((ortalama_satis * tedarik_suresi) + emniyet_stoku)
guncel_stok = df_secilen['Mevcut_Stok'].iloc[-1]

# Aksiyon Kararı ve Yok Satma Riski
siparis_miktari = 0
kacan_firsat_maliyeti = 0
if guncel_stok <= yeniden_siparis_noktasi:
    siparis_miktari = yeniden_siparis_noktasi + emniyet_stoku - guncel_stok
    eksik_miktar = max(0, yeniden_siparis_noktasi - guncel_stok)
    kacan_firsat_maliyeti = eksik_miktar * birim_kar

# Finansal Metrikler
bagli_sermaye = guncel_stok * birim_urun_maliyeti
yillik_stok_maliyeti = bagli_sermaye * elde_tutma_orani

toplam_satis_periyot = df_secilen['Satis_Adedi'].sum()
ortalama_stok_periyot = df_secilen['Mevcut_Stok'].mean()
devir_hizi = toplam_satis_periyot / ortalama_stok_periyot if ortalama_stok_periyot > 0 else 0
yillik_tahmini_devir_hizi = devir_hizi * (365 / len(df_secilen))

# ANA EKRAN VE SEKMELER
st.subheader(t(f"Analiz Edilen Ürün: {secilen_urun}", f"Analyzed Product: {secilen_urun}"))

tab_titles = [
    t("Ana Planlama Paneli", "Main Planning Panel"), 
    t("İPK Talep Kontrol Grafiği", "SPC Demand Control Chart"), 
    t("Kurumsal ABC Analizi", "Corporate ABC Analysis"), 
    t("Ham Veri Seti", "Raw Data Set")
]
tab1, tab2, tab3, tab4 = st.tabs(tab_titles)

with tab1:
    st.markdown(t("#### Operasyonel Envanter Parametreleri", "#### Operational Inventory Parameters"))
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(t("Ortalama Günlük Satış", "Average Daily Sales"), f"{ortalama_satis:.1f}")
    col2.metric(t("Önerilen Emniyet Stoku", "Recommended Safety Stock"), str(emniyet_stoku))
    col3.metric(t("Sipariş Noktası (ROP)", "Reorder Point (ROP)"), str(yeniden_siparis_noktasi))
    col4.metric(t("Güncel Depo Stoğu", "Current Inventory"), str(guncel_stok))

    st.markdown("---")
    if siparis_miktari > 0:
        st.error(t(
            f"KRİTİK UYARI: Mevcut stok ({guncel_stok}), ROP ({yeniden_siparis_noktasi}) seviyesinin altına inmiştir.",
            f"CRITICAL WARNING: Current inventory ({guncel_stok}) has dropped below the ROP ({yeniden_siparis_noktasi}) level."
        ))
        st.warning(t(
            f"Zorunlu Aksiyon: Tedarik sürecinin kesintiye uğramaması için net {siparis_miktari} adet yeni sipariş/iş emri açılmalıdır.",
            f"Mandatory Action: To prevent supply chain disruption, a new order/work order for exactly {siparis_miktari} units must be placed."
        ))
    else:
        st.success(t(
            "SİSTEM ONAYI: Mevcut stok seviyesi, hedeflenen hizmet kalitesini sağlamak için yeterlidir.",
            "SYSTEM APPROVAL: The current inventory level is sufficient to maintain the targeted service quality."
        ))

    st.markdown("---")
    st.markdown(t("#### Finansal Performans ve Risk Analizi", "#### Financial Performance & Risk Analysis"))
    f_col1, f_col2, f_col3 = st.columns(3)
    f_col1.info(t(
        f"Bağlı Sermaye (Durağan Nakit):\n\n{bagli_sermaye:,.2f}",
        f"Tied-up Capital (Idle Cash):\n\n{bagli_sermaye:,.2f}"
    ))
    f_col2.warning(t(
        f"Yıllık Elde Tutma Maliyeti:\n\n{yillik_stok_maliyeti:,.2f}",
        f"Annual Holding Cost:\n\n{yillik_stok_maliyeti:,.2f}"
    ))
    
    if kacan_firsat_maliyeti > 0:
        f_col3.error(t(
            f"Yok Satma Riski (Kaçan Kar):\n\n{kacan_firsat_maliyeti:,.2f}",
            f"Stockout Risk (Lost Profit):\n\n{kacan_firsat_maliyeti:,.2f}"
        ))
    else:
        f_col3.success(t(
            f"Tahmini Stok Devir Hızı:\n\nYılda {yillik_tahmini_devir_hizi:.1f} Dönüş",
            f"Estimated Inventory Turnover:\n\n{yillik_tahmini_devir_hizi:.1f} Turns/Year"
        ))

    st.markdown("---")
    st.markdown(t("#### Stok Seviyesi Düşüş Simülasyonu", "#### Inventory Level Depletion Simulation"))
    st.line_chart(df_secilen.set_index('Tarih')['Mevcut_Stok'])

with tab2:
    st.markdown(t(
        "#### İstatistiksel Proses Kontrol (İPK) - Talep Dağılım Analizi", 
        "#### Statistical Process Control (SPC) - Demand Distribution Analysis"
    ))
    st.markdown(t(
        "Aşağıdaki kontrol grafiği (Control Chart), günlük müşteri taleplerinin sistemin tasarlandığı varyans limitleri içinde kalıp kalmadığını denetler. Çizgilerin hangi veriyi temsil ettiğini grafiğin altındaki lejanttan görebilirsiniz. Değerlerin UCL üzerine çıkması kalıcı bir talep patlamasına işaret edebilir.",
        "The control chart below monitors whether daily customer demands remain within the designed variance limits of the system. You can see what each line represents in the legend below the chart. Values exceeding the UCL may indicate a permanent demand surge."
    ))
    
    # Sütun ismini dile göre dinamik olarak belirliyoruz
    satis_etiketi = t('Satış Miktarı', 'Sales Quantity')
    
    chart_df = df_secilen[['Tarih', 'Satis_Adedi']].copy()
    
    # Grafiğe basmadan önce orijinal "Satis_Adedi" sütun ismini profesyonel etiketle değiştiriyoruz
    chart_df.rename(columns={'Satis_Adedi': satis_etiketi}, inplace=True)
    chart_df.set_index('Tarih', inplace=True)
    
    chart_df[t('Ortalama (CL)', 'Average (CL)')] = ortalama_satis
    chart_df[t('Üst Kontrol Limiti (UCL)', 'Upper Control Limit (UCL)')] = ortalama_satis + (3 * standart_sapma_satis)
    chart_df[t('Alt Kontrol Limiti (LCL)', 'Lower Control Limit (LCL)')] = max(0, ortalama_satis - (3 * standart_sapma_satis))
    
    st.line_chart(chart_df)

with tab3:
    st.markdown(t("#### Kurumsal Portföy ABC Sınıflandırması", "#### Corporate Portfolio ABC Classification"))
    st.markdown(t(
        "Sistemdeki tüm ürünler, firmaya getirdikleri toplam finansal hacme göre otomatik olarak kategorize edilmiştir. Pareto kuralı gereği, 'A Sınıfı' ürünler finansal dengenin belkemiğidir ve en yüksek Müşteri Hizmet Seviyesi ile kontrol edilmelidir.",
        "All products in the system are automatically categorized based on their total financial volume contribution to the company. According to the Pareto principle, 'Class A' products are the backbone of financial stability and should be controlled with the highest Customer Service Level."
    ))
    
    gosterim_df = abc_df[['Urun_Adi', 'Hacim', 'Kümülatif_Yüzde', 'ABC_Sinifi']].copy()
    gosterim_df.columns = [
        t('Ürün Adı', 'Product Name'), 
        t('Toplam Finansal Hacim', 'Total Financial Volume'), 
        t('Kümülatif Değer Oranı', 'Cumulative Value Ratio'), 
        t('Öncelik Sınıfı', 'Priority Class')
    ]
    
    gosterim_df[t('Kümülatif Değer Oranı', 'Cumulative Value Ratio')] = gosterim_df[t('Kümülatif Değer Oranı', 'Cumulative Value Ratio')].apply(lambda x: f"%{x*100:.1f}" if secilen_dil == "Türkçe" else f"{x*100:.1f}%")
    
    st.dataframe(gosterim_df, use_container_width=True)

with tab4:
    st.markdown(t("#### Satış Geçmişi ve Ham Veri Seti", "#### Sales History and Raw Data Set"))
    
    gosterim_ham_df = df_secilen.copy()
    if secilen_dil == "English":
        gosterim_ham_df.rename(columns={
            'Tarih': 'Date',
            'Urun_ID': 'Product_ID',
            'Urun_Adi': 'Product_Name',
            'Satis_Adedi': 'Sales_Quantity',
            'Mevcut_Stok': 'Current_Inventory',
            'Tedarik_Suresi_Gun': 'Lead_Time_Days'
        }, inplace=True)
        
    st.dataframe(gosterim_ham_df, use_container_width=True)