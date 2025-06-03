import google.generativeai as genai

# GEÇERLİ API ANAHTARINIZI BURAYA YAPIŞTIRIN
genai.configure(api_key="AIzaSyAa-NZUbJCHGJPdWzgVh6Rb8WEZkUZJIeU")

try:
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content("Merhaba de.")
    print("API Bağlantısı Başarılı!")
    print("Modelin Yanıtı:", response.text)
except Exception as e:
    print("API Bağlantısı HATALI!")
    print("Hata Mesajı:", e)