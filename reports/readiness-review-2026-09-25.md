# Apteka: 2026-09-25 yakuniy tekshiruv

Mavjud dizayn va loyiha tuzilishi saqlandi. Ishchi ma’lumotlar tahrirlanmadi.
Boshlang‘ich 66 test o‘tdi; yangi regressiya testlari bilan 70 test o‘tdi.

## Topilgan va tuzatilgan muammolar

1. Oldin ochilgan admin/katalog tahrir formasi sotuvdan keyingi qoldiq ustiga eski
   sonni yozishi mumkin edi. Har bir mavjud joylashuvga imzolangan holat qo‘shildi;
   o‘zgargan holat rad etiladi. POST tranzaksiyasida dori va joylashuv qulflanadi.
2. Smena ochilmagan holdagi bo‘sh POST sotuv formasida server xatosiga sabab
   bo‘lishi mumkin edi. Bo‘sh POST ham bog‘langan forma sifatida tekshiriladi.
3. Rus tilida qadoq haqidagi bo‘sh qiymat matni va ko‘chirish tarixidagi polka/qator
   yozuvlari o‘zbekcha qolgan. Ko‘rinadigan matn tarjima qilindi; bazadagi tarix,
   dori nomlari va bo‘lim nomlari o‘zgarmadi.
4. `DB_ENGINE` xato yozilsa SQLite avtomatik tanlanardi. Endi noma’lum qiymat
   konfiguratsiya xatosi bilan to‘xtaydi.
5. Ko‘chirishda manba tranzaksiya ichida qayta o‘qiladi va qulflanadi.
6. Eski brauzer skripti til tugmasini kirish tugmasi deb bosardi; Playwright
   kontekstida sinxron ORM chaqirar va navigatsiya tugashini kutmas edi.
   Skript tuzatildi va bekor qilish jarayoni ham qo‘shildi.

## Tekshirilgan ishlar

- Dori qo‘shish/tahrirlash, joylashuv va partiya sanasi, Unicode/faol modda bo‘yicha
  qidirish, narx va qoldiq ko‘rsatish.
- Smena → sotuvni tayyorlash → tasdiqlash → aynan tanlangan joy/partiyadan ayirish.
- Yetarli bo‘lmagan, muddati o‘tgan yoki sanasi noma’lum partiyani sotishni rad etish.
- Ikki alohida ulanishdagi parallel sotuv: biri sotadi, ikkinchisi rad etiladi;
  parallel bekor qilish qoldiqni faqat bir marta qaytaradi.
- Bekor qilingan savdolar hisobot tushumidan chiqariladi, tarix saqlanadi.
- URL orqali ruxsatsiz kirish, boshqa xodim smenasi/sotuviga kirish va CSRF himoyasi.
- O‘zbekcha/ruscha admin ichki sahifalari, formalar, xabarlar, til almashish,
  faqat ochilgan bo‘lim navigatsiyasining faolligi.
- Chromium: kirish, smena, 3 × 1250.50 = 3751.50, qoldiq 10 → 7 → 10,
  bekor qilish, rus tili va joriy bo‘lim tugmasi.

Buyruqlar: `manage.py test --noinput` (70 test), `scripts/browser_workflow.py`
(1 test), `manage.py makemigrations --check --dry-run`, `manage.py check --deploy`,
`manage.py collectstatic --noinput`, `manage.py backup_sqlite ...` — muvaffaqiyatli.
Testlar alohida test bazalarida bajarildi. Server sozlamalari testi vaqtinchalik
muhit kaliti bilan bajarildi; haqiqiy maxfiy kalit kodga kiritilmadi.

## Ma’lumotlar saqlanishi

Asl `db.sqlite3` SHA-256 tekshiruvdan oldin va keyin bir xil:
`89d39fbc4e75da24d8490c066a8ddc31b48a64b571e654eb4f89cc4ae68d90e3`.
4 dori, 4 partiya, 5 joylashuv, 0 sotuv, 1 smena bor edi va saqlandi.
`/tmp/apteka-readiness-20260925.sqlite3` izchil nusxasi yaratildi; asl va nusxa
`PRAGMA integrity_check`dan o‘tdi, jadval sonlari mos. `/tmp` uzoq muddatli backup
saqlash joyi emas; doimiy tashqi nusxa uchun DEPLOYMENT.md tartibini bajaring.
Yangi migratsiya kerak bo‘lmadi.

## Chegaralar va keyingi tashqi ishlar

- PostgreSQL mavjud emas: unda ushbu testlar bajarilmadi. SQLite parallel ulanish
  testlari o‘tdi; PostgreSQL tayyor deb belgilanmaydi.
- Haqiqiy server, DNS, TLS, Nginx/Gunicorn va tashqi backup jadvali o‘rnatilmadi.
  Bular uchun server rekvizitlari va domen kerak.
- Narx mavjud model bo‘yicha dori darajasida, barcha partiyalar uchun umumiy.
  Qoldiq, yaroqlilik va joylashuv partiya bo‘yicha alohida.
- Tibbiy ma’lumotlarning mazmuniy to‘g‘riligi tekshirilmadi; testlar dastur
  funksiyalarini tekshiradi. Mavjud noma’lum yaroqlilik sanalari taxminan to‘ldirilmadi.

Lokal va server buyruqlari, muhit o‘zgaruvchilari, PostgreSQLga ko‘chirish,
backup va tiklash: [DEPLOYMENT.md](../DEPLOYMENT.md).
