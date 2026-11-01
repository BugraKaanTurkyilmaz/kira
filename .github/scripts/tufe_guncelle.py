#!/usr/bin/env python3
"""Yasal kira artış sınırını (TÜFE 12 aylık ortalama değişimi) kaynaklardan okuyup tufe.json'ı günceller.

Kaynaklar tarayıcıdan okunamadığı için (CORS) bu iş GitHub Actions'ta yapılır.
- BTSO: TÜİK'in açıkladığı oranı olduğu gibi yayımlar, asıl kaynak budur.
- TCMB: aylık değişimlerden oran hesaplanır. BTSO'yu sınamak için kullanılır;
  BTSO henüz güncellenmediyse yeni oran geçici olarak buradan alınır.

Çıkış kodu 1: kaynaklar okundu ama sonuç güvenilir değil, tufe.json'a dokunulmaz.
"""
import datetime
import html
import json
import pathlib
import re
import sys
import urllib.request

TUFE_JSON = pathlib.Path(__file__).resolve().parents[2] / "tufe.json"
BTSO_URL = "https://www.btso.org.tr/bilgi-bankasi/istatistikler-ve-raporlar/ufe-tufe-oranlari/{yil}"
TCMB_URL = "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Istatistikler/Enflasyon+Verileri/Tuketici+Fiyatlari"
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
# Aylık veriler iki haneye yuvarlı olduğu için hesap son hanede sapabilir.
TOLERANS = 0.02


class Guvenilmez(Exception):
    pass


def indir(url):
    istek = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (kira-defteri tufe guncelleme)"})
    with urllib.request.urlopen(istek, timeout=30) as yanit:
        return yanit.read().decode("utf-8", "replace")


def satirlar(sayfa):
    for satir in re.findall(r"<tr.*?</tr>", sayfa, re.S):
        hucreler = re.findall(r"<t[dh].*?</t[dh]>", satir, re.S)
        yield [" ".join(html.unescape(re.sub(r"<[^>]+>", " ", h)).split()) for h in hucreler]


def btso_oranlari(sayfa):
    """{"2026-09": 31.49, ...}: veri ayına göre açıklanan 12 aylık ortalama değişimi."""
    oranlar, ay = {}, None
    for h in satirlar(sayfa):
        if len(h) != 3:
            continue
        baslik = re.fullmatch(r"(\w+) - (\d{4})", h[0])
        if baslik and baslik[1] in AYLAR:
            ay = f"{baslik[2]}-{AYLAR.index(baslik[1]) + 1:02d}"
        elif ay and h[0].startswith("Oniki Aylık"):
            oranlar[ay] = float(h[2].replace(",", "."))
    return oranlar


def tcmb_oranlari(sayfa):
    """Aylık değişimlerden endeks zinciri kurup her ay için 12 aylık ortalama değişimi hesaplar."""
    aylik = {}
    for h in satirlar(sayfa):
        if len(h) == 3 and re.fullmatch(r"\d{2}-\d{4}", h[0]):
            aylik[f"{h[0][3:]}-{h[0][:2]}"] = float(h[2])
    aylar = sorted(aylik)
    endeks = [100.0]
    for ay in aylar[1:]:
        endeks.append(endeks[-1] * (1 + aylik[ay] / 100))
    return {
        aylar[i]: round((sum(endeks[i - 11:i + 1]) / sum(endeks[i - 23:i - 11]) - 1) * 100, 2)
        for i in range(23, len(aylar))
    }


def kaynaktan(okuyucu, *urller):
    """Kaynak açılamıyorsa None döner (geçici olabilir); sayfa açılıp veri çıkmıyorsa biçimi değişmiştir."""
    oranlar, acildi = {}, False
    for url in urller:
        try:
            sayfa = indir(url)
        except OSError as e:
            print(f"uyarı: {url} okunamadı: {e}")
            continue
        acildi = True
        oranlar.update(okuyucu(sayfa))
    if not acildi:
        return None
    if not oranlar:
        raise Guvenilmez(f"sayfa biçimi değişmiş olabilir: {urller[0]}")
    return oranlar


def sonraki_ay(ym):
    y, a = map(int, ym.split("-"))
    return f"{y + (a == 12)}-{a % 12 + 1:02d}"


def sonuc(btso, tcmb):
    """(veri ayı, oran, kaynak metni) döner. tufeAy veri ayının bir sonraki ayıdır."""
    btso, tcmb = btso or {}, tcmb or {}
    for ay in btso.keys() & tcmb.keys():
        if abs(btso[ay] - tcmb[ay]) > TOLERANS:
            raise Guvenilmez(f"{ay} için kaynaklar uyuşmuyor: BTSO {btso[ay]}, TCMB hesabı {tcmb[ay]}")
    b, t = max(btso, default=""), max(tcmb, default="")
    if not b and not t:
        return None
    ay = max(b, t)
    ad = f"{AYLAR[int(ay[5:]) - 1]} {ay[:4]}"
    if ay == b:
        return ay, btso[ay], f"TÜİK ({ad} verisi)"
    return ay, tcmb[ay], f"TCMB aylık verisinden hesaplandı ({ad} verisi)"


def main():
    yil = datetime.date.today().year
    btso = kaynaktan(btso_oranlari, BTSO_URL.format(yil=yil - 1), BTSO_URL.format(yil=yil))
    tcmb = kaynaktan(tcmb_oranlari, TCMB_URL)
    bulunan = sonuc(btso, tcmb)
    if not bulunan:
        print("uyarı: iki kaynak da okunamadı, sonraki çalışmada yeniden denenecek")
        return
    ay, oran, kaynak = bulunan
    if not 0 < oran < 200:
        raise Guvenilmez(f"oran makul aralıkta değil: {oran}")

    eski = json.loads(TUFE_JSON.read_text(encoding="utf-8"))
    tufe_ay = sonraki_ay(ay)
    if tufe_ay < eski["tufeAy"]:
        print(f"değişiklik yok: {tufe_ay} kayıtlı aydan ({eski['tufeAy']}) eski")
        return
    if (oran, tufe_ay, kaynak) == (eski["tufe"], eski["tufeAy"], eski["kaynak"]):
        print(f"değişiklik yok: %{oran} ({tufe_ay})")
        return
    yeni = {"tufe": oran, "tufeAy": tufe_ay, "kaynak": kaynak, "guncelleme": datetime.date.today().isoformat()}
    TUFE_JSON.write_text(json.dumps(yeni, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"güncellendi: %{oran} ({tufe_ay}), {kaynak}")


if __name__ == "__main__":
    try:
        main()
    except Guvenilmez as e:
        print(f"hata: {e}")
        sys.exit(1)
