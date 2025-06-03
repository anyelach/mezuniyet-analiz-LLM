from flask import Flask, request, jsonify, render_template
import os
import re
import json
import fitz  # PyMuPDF
import google.generativeai as genai
from werkzeug.utils import secure_filename 

app = Flask(__name__)

# Google Gemini API Anahtarı
genai.configure(api_key="AIzaSyAa-NZUbJCHGJPdWzgVh6Rb8WEZkUZJIeU") 

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


    

# Ders Planı JSON'u yükle
try:
    with open('dersler.json', encoding='utf-8') as f:
        all_courses = json.load(f)
except FileNotFoundError:
    print("Hata: 'dersler.json' dosyası bulunamadı. Lütfen dosyanızın uygulamanızla aynı dizinde olduğundan emin olun.")
    all_courses = {"dersPlani": []} # Hata durumunda boş bir yapı ata

# CID Temizleme haritası
# ÖNEMLİ: Bozuk karakterlerin başında 'r' ekleyerek raw string (ham string) yaptık.
# Bu, Python'ın \U, \D gibi dizileri özel karakterler olarak yorumlamasını engeller.
cid_map = {
    # Mevcutlar
    "248": "İ",
    "213": "ı",
    # Yeni eklemeler veya güncellemeler (terminal çıktınıza göre)
    r"BMı": "BM213", # Bu çok önemli!
    r"$WDWUNøONHOHULYHøQNÕODS7DULKL,": "Atatürk İlkeleri ve İnkılap Tarihi",
    r"%LOJLVD\DU0KHQGLVOL÷LQH*LULú": "Bilgisayar Mühendisliğine Giriş",
    r"%LOLúLP7HNQRORMLOHUL": "Bilişim Teknolojileri",
    r"øQJLOL]FH,": "İngilizce",
    r"2ODVÕOÕNYHøVWDWLVWLN": "Olasılık ve İstatistik",
    r"1HVQH\H'D\DOÕ3URJUDPODPD": "Nesneye Dayalı Programlama",
    r"6D\ÕVDO$QDOL]": "Sayısal Analiz",
    r"$\UÕNøúOHPVHO<DSÕODU": "Ayrık İşlemsel Yapılar",
    r"6D\ÕVDO(OHNWURQLN": "Sayısal Elektronik",
    r"1HVQH\H'D\DOÕ$QDOL]YH7DVDUÕP": "Nesneye Dayalı Analiz ve Tasarım",
    r"0HVOHNLøQJLOL]FH": "Mesleki İngilizce",
    r"9HUL<DSÕODUÕ": "Veri Yapıları",
    r"øúDUHWOHUYH6LVWHPOHU": "İşaretler ve Sistemler",
    r"øúOHWLP6LVWHPOHUL": "İşletim Sistemleri",
    r"%LOJLVD\DU$÷ODUÕ,": "Bilgisayar Ağları",
    r"9HULWDEDQÕ<|QHWLP6LVWHPOHUL": "Veritabanı Yönetim Sistemleri",
    r"<D]'|QHPL6WDMÕ,": "Yaz Dönemi Stajı",
    r"0KHQGLVOLN(WL÷L": "Mühendislik Etiği",
    r"%LOJLVD\DU$÷ODUÕ,,": "Bilgisayar Ağları II",
    r"0LNURLúOHPFLOHU": "Mikroişlemciler",
    r"<D]ÕOÕS0KHQGLVOL÷L": "Yazılım Mühendisliği",
    r"%LOJLVD\DU0KHQGLVOL÷L3URMH\nTasarımı": "Bilgisayar Mühendisliği Proje Tasarımı", # Ders adı iki satıra yayılmış
    r"%XODQÕN0DQWÕ÷D*LULú": "Bulanık Mantığa Giriş",
    r"0DNLQHg÷UHQmeVLQH*LULú": "Makine Öğrenmesine Giriş", # Küçük harf hatası var, düzeltin
    r"9HULøOHWLúLPL": "Veri İletişimi",
    r"<D]'|QHPL6WDMÕ,,": "Yaz Dönemi Stajı II",
    r"'HUV$GÕ": "Ders Adı", # Başlıklar da bozulmuş, temizleyin
    r"7&.ø0/ø.12": "TC KİMLİK NO",
    r"$,/,ù7$5ø+ø": "AYRILIŞ TARİHİ",
    r".$,77$5ø+ø": "KAYIT TARİHİ",
    r"gö5(1&ø180$5$6,": "ÖĞRENCİ NUMARASI",
    r"%LOJLVD\DU0KHQGLVOL÷L1g": "Bilgisayar Mühendisliği N.Ö.",
    r")$.h/7(6ø": "FAKÜLTESİ",
    r"øOLúLNNHVPHVHELEXOXQDPDGÕ": "İlişik kesme sebebi bulunamadı",
    r"6WDMELOJLVLEXOXQDPDGÕ": "Staj bilgisi bulunamadı",
    r"+D]ÕUOÕN2NXPDPÕú": "Hazırlık Okumamış",
    r"+D]ÕUOÕN'XUXPX": "Hazırlık Durumu",
    r"(*)LOHLúDUHWOHQHQGHUVOHU(UDVPXV3URJUDPÕNDSVDPÕQGDDOÕQPÕúWÕU": "(*) ile işaretlenen dersler Erasmus Programı kapsamında alınmıştır",
    r"(**)LOHLúDUHWOHQHQGHUVOHU)DUDEL3URJUDPÕNDSVDPÕQGDDOÕQPÕúWÕU": "(**) ile işaretlenen dersler Farabi Programı kapsamında alınmıştır"
    # Ek olarak, eğer sadece bir karakter bozulmuşsa onu da ekleyin (örn. ı, ö vb.)
}


def cid_temizle(metin):
    if not isinstance(metin, str):
        return metin
    # Önce cid_map'teki bozuk kelimeleri düzeltelim
    for bozuk, duzgun in cid_map.items():
        # r string'i kullandığımız için bozuk kelimeleri doğrudan kullanabiliriz.
        # replace() ile bozuk kelimeyi düzgün kelimeyle değiştiriyoruz.
        # Not: bozuk kelime string'in herhangi bir yerinde olabilir, bu yüzden doğrudan replace uygundur.
        metin = metin.replace(bozuk, duzgun)
    
    # Sonra (cid:xxx) formatındaki karakterleri düzeltelim (eğer hala varsa)
    def degistir(match):
        # Bu kısım mevcut cid:xxx formatı için. Eğer böyle bir format kalmazsa, bu map boş kalabilir.
        return cid_map.get(match.group(1), '')
    return re.sub(r'\(cid:(\d+)\)', degistir, metin)

# ... (kodun geri kalanı aynı) ...

def extract_text_from_pdf(pdf_path):
    """PDF dosyasından metin çıkarır."""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close() 
    
    # Ham metin alındıktan sonra cid_temizle ile karakter bozulmalarını düzeltiyoruz.
    temizlenmis_text = cid_temizle(text)

    print("\n🧾 PDF'ten alınan ham metin (ilk 500 karakter):")
    print(temizlenmis_text[:500] + "..." if len(temizlenmis_text) > 500 else temizlenmis_text) 
    print("\n--- PDF'ten Çıkarılan ve TEMİZLENEN Ham Metnin Tamamı (Lütfen İncele!) ---")
    print(temizlenmis_text) 
    print("---------------------------------------------------------")
    return temizlenmis_text

def extract_ders_bilgileri(text):
    """Çıkarılan metinden ders bilgilerini (kod, isim, kredi, akts, not) ayrıştırır."""
    dersler = []

    # Bu format için en iyi regex: (Buradaki girinti önemli)
    pattern = r"([A-Z]{2,4}\d{3})\s*\n(.+?)\s*\n(\d+(?:\.\d{1,2})?)\s*\n(\d+(?:\.\d{1,2})?)\s*\n([A-Z]{1,2}|YT|YZ|GR|DV)"
    
   
    matches = re.findall(pattern, text, re.DOTALL) 
    
    for match in matches:
        ders_kodu, ders_ismi, kredi, akts, harf_notu = match
        dersler.append((ders_kodu.strip(), ders_ismi.strip(), kredi.strip(), akts.strip(), harf_notu.strip()))
    
    print("\n🔍 Çıkarılan dersler:")
    if not dersler: 
        print("Hata: Hiç ders bulunamadı! Lütfen regex desenini veya PDF metin çıkarımını kontrol edin.")
    else:
        for d in dersler:
            print(f"  - {d[0]} - {d[1]} - {d[4]}")
    return dersler

def extract_course_codes(dersler):
    """Alınan derslerin kodlarını döndürür."""
    return list(set(d[0] for d in dersler))

def calculate_missing_required(all_courses_json, taken_codes):
    """Ders planına göre eksik zorunlu dersleri hesaplar."""
    required = set() 
    for semester in all_courses_json["dersPlani"]:
        for course in semester["zorunluDersler"]:
            if course.get("zorunluMu", True): 
                required.add(course["kodu"].replace(" ", ""))
    return sorted([k for k in required if k not in taken_codes]) 

def mezuniyet_hesapla(dersler, all_courses_json): 
    """Öğrencinin mezuniyet kriterlerini kontrol eder ve eksikleri listeler."""
    hatalar = []

    # Zorunlu ders kodlarını all_courses_json'dan çek
    zorunlu_ders_kodlari_sistem = set()
    for semester in all_courses_json["dersPlani"]:
        for course in semester["zorunluDersler"]:
            if course.get("zorunluMu", True): 
                zorunlu_ders_kodlari_sistem.add(course["kodu"].replace(" ", ""))

    # 1. Toplam AKTS kontrolü
    toplam_akts = sum(float(d[3]) for d in dersler)
    if toplam_akts < 240:
        hatalar.append(f"Toplam AKTS yetersiz (Şu anki AKTS: {toplam_akts}).")

    # 2. Aynı ders birden fazla kez alınmış mı kontrolü
    ders_kodlari_sadece_kod = [d[0] for d in dersler]
    from collections import Counter
    tekrar_edenler = [item for item, count in Counter(ders_kodlari_sadece_kod).items() if count > 1]
    if tekrar_edenler:
        hatalar.append(f"Aynı ders birden fazla kez alınmış: {', '.join(sorted(tekrar_edenler))}.")

    # 3. Üniversite seçmeli (US) ders kontrolü
    if not any(d[0].startswith("US") for d in dersler):
        hatalar.append("En az 1 üniversite seçmeli (US kodlu) ders alınmamış.")
    
    # 4. Fakülte seçmeli (MS) ders kontrolü
    if not any(d[0].startswith("MS") for d in dersler):
        hatalar.append("En az 1 fakülte seçmeli (MS kodlu) ders alınmamış.")

    # 5. Bölüm seçmeli dersler (BM4xx veya MTH4xx ve zorunlu olmayanlar) kontrolü
    secmeli_dersler_sayisi = 0
    alinan_bolum_secmeli_kodlari = [] 
    for d_kodu, _, _, _, _ in dersler:
        if (d_kodu.startswith("BM4") or d_kodu.startswith("MTH4")) and d_kodu not in zorunlu_ders_kodlari_sistem:
            secmeli_dersler_sayisi += 1
            alinan_bolum_secmeli_kodlari.append(d_kodu)
    
    if secmeli_dersler_sayisi < 10:
        alinan_secmeli_str = f" ({secmeli_dersler_sayisi} tane var"
        if alinan_bolum_secmeli_kodlari:
            alinan_secmeli_str += f": {', '.join(sorted(set(alinan_bolum_secmeli_kodlari)))}"
        else:
            alinan_secmeli_str += ", hiç bölüm seçmeli alınmamış"
        alinan_secmeli_str += ")"
        hatalar.append(f"Yeterli sayıda (10 adet) BM4xx veya MTH4xx kodlu bölüm seçmeli dersi yok.{alinan_secmeli_str}")

    # 6. Yaz Stajı Kontrolü - Düzeltildi
    yaz_staji = [d for d in dersler if d[0] in ("BM399", "BM499")]
    if not yaz_staji:
        hatalar.append("Yaz stajı tamamlanmamış (BM399 veya BM499 alınmamış).")
    elif any(d[4] == "YZ" for d in yaz_staji): 
        hatalar.append("Yaz stajı derslerinden (BM399 veya BM499) birinin notu YZ (Yetersiz).") 

    # 7. Başarısız ders kontrolü
    basarisiz_notlar = {"FF", "FD", "YZ"}
    basarisiz = [d for d in dersler if d[4] in basarisiz_notlar]
    if basarisiz:
        kodlar = ", ".join(sorted(set(d[0] for d in basarisiz))) 
        hatalar.append(f"Başarısız ders(ler): {kodlar}")

    return hatalar

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        if 'transcript' not in request.files:
            return jsonify({"error": "PDF yüklenmedi"}), 400

        file = request.files['transcript']
        filename = secure_filename(file.filename) 
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)

        text = extract_text_from_pdf(path)
        dersler = extract_ders_bilgileri(text)
        ders_kodlari = extract_course_codes(dersler)
        
        eksik_zorunlu = calculate_missing_required(all_courses, ders_kodlari)
        hatalar_sistem = mezuniyet_hesapla(dersler, all_courses) 

        # LLM için gerekli bilgileri topla
        toplam_akts_llm = sum(float(d[3]) for d in dersler)
        
        yaz_staji_dersleri_llm = [d for d in dersler if d[0] in ("BM399", "BM499")]
        if not yaz_staji_dersleri_llm:
            yaz_staji_durumu_llm = "Alınmamış."
        elif any(d[4] == "YZ" for d in yaz_staji_dersleri_llm):
            yaz_staji_durumu_llm = "Notu YZ (Yetersiz)."
        elif any(d[4] == "YT" for d in yaz_staji_dersleri_llm): 
            yaz_staji_durumu_llm = "Tamamlandı (YT notu ile)."
        else: 
            yaz_staji_durumu_llm = "Tamamlandı (Geçerli not ile)."


        basarisiz_dersler_llm_list = sorted(set(d[0] for d in dersler if d[4] in {"FF", "FD", "YZ"}))
        basarisiz_dersler_llm = ", ".join(basarisiz_dersler_llm_list) or 'Yok'

        zorunlu_ders_kodlari_all_for_llm = set()
        for semester in all_courses["dersPlani"]:
            for course in semester["zorunluDersler"]:
                if course.get("zorunluMu", True): 
                    zorunlu_ders_kodlari_all_for_llm.add(course["kodu"].replace(" ", ""))

        secmeli_ders_sayisi_llm = 0
        alinan_bolum_secmeli_kodlari_llm = []
        for d_kodu, _, _, _, _ in dersler:
            if (d_kodu.startswith("BM4") or d_kodu.startswith("MTH4")) and d_kodu not in zorunlu_ders_kodlari_all_for_llm:
                secmeli_ders_sayisi_llm += 1
                alinan_bolum_secmeli_kodlari_llm.append(d_kodu)
        alinan_secmeli_ders_kodlari_llm_str = ", ".join(sorted(set(alinan_bolum_secmeli_kodlari_llm))) or 'Yok'


        llm_yorum_metni = ""
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(
                f"""
Sen bir üniversite mezuniyet memurusun. Aşağıdaki öğrencinin transkript bilgilerini ve sistem tarafından yapılan ön analiz sonuçlarını kullanarak mezuniyet durumunu değerlendir ve eksiklerini belirt.

Teknik Mezuniyet Kuralları:
- Toplam AKTS en az 240 olmalı.
- Aynı ders birden fazla alınamaz.
- En az 1 US kodlu (Üniversite Seçmeli) ders olmalı.
- En az 1 MS kodlu (Fakülte Seçmeli) ders olmalı.
- En az 10 tane BM4xx veya MTH4xx kodlu BÖLÜM SEÇMELİ ders olmalı. Bu kodlar, zorunlu dersler arasında yer almamalıdır (örneğin BM401 ve BM498 dersleri zorunludur ve seçmeli sayılmaz).
- BM399 ve/veya BM499 derslerinden biri alınmalı ve notu YZ (Yetersiz) olmamalıdır. YT (Yeterli) notu geçerlidir.
- FD, FF, YZ notu olan dersler başarısız sayılır.

Sistem Tarafından Çıkarılan Detaylı Bilgiler:
- Öğrencinin aldığı ders kodları: {", ".join(sorted(ders_kodlari))}
- Toplam AKTS: {toplam_akts_llm}
- Yaz Stajı Durumu: {yaz_staji_durumu_llm}
- Başarısız Dersler: {basarisiz_dersler_llm}
- Alınan Bölüm Seçmeli Ders Sayısı (BM4xx/MTH4xx ve zorunlu olmayanlar): {secmeli_ders_sayisi_llm} ({alinan_secmeli_ders_kodlari_llm_str})
- Üniversite Seçmeli Ders Durumu: {'Alınmış' if any(d[0].startswith("US") for d in dersler) else 'Alınmamış'}
- Fakülte Seçmeli Ders Durumu: {'Alınmış' if any(d[0].startswith("MS") for d in dersler) else 'Alınmamış'}
- Eksik Zorunlu Dersler (Sistem tarafından hesaplanan): {", ".join(eksik_zorunlu) or 'Yok'}
- Mezuniyet Hesaplama Fonksiyonundan Gelen Diğer Hatalar: {", ".join(hatalar_sistem) or 'Yok'}

Değerlendirmeni sadece yukarıdaki bilgiler ışığında, aşağıdaki formatta yap. Mezuniyet durumunu net bir şekilde belirt ve varsa tüm eksiklikleri madde madde listele. Gereksiz yorum, övgü veya kariyer tavsiyesi verme.

Örnek çıktılar:
Mezun olabilirsin.

Mezun olamazsın:
- Toplam AKTS yetersiz (Şu anki AKTS: 212).
- Yaz stajı derslerinden (BM399 veya BM499) birinin notu YZ (Yetersiz).
- Başarısız ders(ler): BM309, BM499
- Yeterli sayıda (10 adet) BM4xx veya MTH4xx kodlu bölüm seçmeli dersi yok. (Şu an 6 tane var: BM401, BM430, BM455, BM469, BM477, BM493)
- Eksik zorunlu dersler: AIB101, TDB121, FIZ111, BM107, MAT111, BM103, BM115, BM111, ING101, AIB102, TDB122, FIZ112, MAT112, BM112, BM114, BM106, KRP102, ING102, BM203, BM213, BM217, BM221, BM223, BM225, BM229, BM204, BM206, BM208, BM210, BM214, BM216, BM301, BM303, BM305, BM307, BM309, BM397, BM302, BM304, BM306, BM308, BM310, BM401, BM497, BM498
"""
            )
            llm_yorum_metni = response.text.strip()

            first_line_llm = llm_yorum_metni.split('\n')[0]
            if "Mezun olabilirsin" in first_line_llm:
                mezuniyet_durumu_display = "✅ Mezun olabilirsin"
            elif "Mezun olamazsın" in first_line_llm:
                mezuniyet_durumu_display = "❌ Mezun olamazsın"
            else:
                mezuniyet_durumu_display = "⁉️ Durum belirlenemedi" 

        except Exception as e:
            print(f"LLM Analiz Hatası: {e}")
            llm_yorum_metni = "LLM analiz hatası oluştu. Lütfen daha sonra tekrar deneyin."
            mezuniyet_durumu_display = "❌ Hata Oluştu"

        return jsonify({
            "mezuniyet_durumu": mezuniyet_durumu_display,
            "llm_yorum": llm_yorum_metni,
            "eksik_zorunlu_dersler": [], 
            "diger_eksikler": [] 
        })

    except Exception as e:
        print(f"Genel Hata: {e}")
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)

