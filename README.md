# Kira Defteri

Telefona kurulabilen kira yönetim uygulaması: kiracılar, mülkler, tahsilat ve makbuz, giderler, raporlar, kira artışı (TÜFE) takibi.

- Veriler sadece kullanıcının telefonunda saklanır (sunucu yok). Ayarlar → Yedek al ile yedeklenir.
- İnternet olmadan da çalışır.
- `tufe.json` GitHub Actions ile otomatik güncellenir: TÜİK'in açıkladığı ayın ilk günlerinde 15 dakikada bir, diğer günler günde bir kontrol edilir. Uygulama yasal kira artış sınırını buradan okur; açıkken 5 dakikada bir ve her öne gelişte yeniden bakar.

## Telefona kurma
- **Android (Chrome):** Sayfayı aç → ⋮ menü → *Uygulamayı yükle* / *Ana ekrana ekle*
- **iPhone (Safari):** Sayfayı aç → Paylaş → *Ana Ekrana Ekle*

## Sürüm yayınlarken
`index.html` içindeki `VERSION`, `sw.js` içindeki `CACHE` adı ve `version.json` birlikte artırılır. Açık uygulamalar `version.json`'a bakıp kendiliğinden yenilenir.
