# Loyiha tekshiruvi — 2026-09-23

Muhammad hisobi bilan Chrome brauzerida kirildi. Yozish amallari /tmp/apteka-audit/db.sqlite3 alohida nusxasida bajarildi. Asosiy katalog va hisob huquqlari o‘zgartirilmadi. Playwright tekshiruv uchun .venv muhitiga o‘rnatildi; loyiha kodi o‘zgartirilmadi.

## Tasdiqlangan xato

**O‘rta daraja — admin paneli dorini joylashuvsiz saqlashga ruxsat beradi.**

`catalog/admin.py:56` dagi PlacementInline uchun yozilgan `validate_min = True` admin formsetida minimal sonni amalda tekshirmayapti.

Takrorlash: administrator bo‘lib mavjud dorining admin tahrirlash sahifasiga kiring, barcha joylashuvlarning o‘chirish belgisini qo‘ying va saqlang. Server 302 qaytaradi, dori saqlanadi, joylashuvlar soni 0 bo‘ladi. `placements-TOTAL_FORMS=0` bilan admin orqali yangi dori yaratish ham qabul qilindi. Oddiy katalog tahrirlash formasi minimal sonni tekshiradi; muammo admin yo‘lida.

Tavsiya: admin inline formsetiga minimal son validatsiyasini aniq uzatish yoki maxsus formset clean usulida tekshirish; barcha joylashuvlarni o‘chirish hamda bo‘sh formset yuborishga regressiya testi qo‘shish. Ushbu auditda xato tuzatilmadi.

## O‘tgan tekshiruvlar

- Mavjud 26 ta Django testi muvaffaqiyatli o‘tdi. Ular rollar, CSRF, HTML escaping, Unicode qidiruv, sahifalash, narx/qoldiq, joylashuvlar va manba/sana validatsiyalarini qamraydi.
- Django oddiy system check: xatosiz. Migratsiyalar to‘liq qo‘llangan; model o‘zgarishi aniqlanmadi. Sinov SQLite bazasining integrity_check natijasi: ok.
- Chrome: noto‘g‘ri parol rad etildi, Muhammad bilan kirish va chiqish ishladi.
- Jonli qidiruv: aniq natija va topilmagan holat ishladi. JavaScript o‘chirilganda ham qidiruv ishladi.
- Dori yaratish, “Yana joylashuv” tugmasi, ikki joydagi jami 12 dona qoldiq, narx/qoldiq tahriri va admin orqali dori o‘chirish ishladi.
- Admin orqali yangi xodim yaratildi; u aptekachi sifatida kirdi. Boshqaruv havolasi ko‘rinmadi; admin, yaratish va tahrirlash URLlari 403 qaytardi.
- Katalog, dori tafsiloti, yaratish va admin bosh sahifalari 320, 390, 768 va 1440 px kengliklarda tekshirildi: gorizontal overflow yo‘q. Mobil katalog va yaratish skrinshotlari ko‘zdan kechirildi.
- Brauzer tekshiruvida JavaScript runtime xatolari: 0.
- Noto‘g‘ri sahifa raqamlari server xatosini keltirib chiqarmadi.

## Joylashtirish holati

`manage.py check --deploy` mahalliy sozlamalarda 6 ta ogohlantirish berdi: DEBUG yoqilgan, ishlab chiqish SECRET_KEY, HTTPS redirect va HSTS sozlanmagan, session hamda CSRF cookie secure bayroqlari o‘chirilgan. Internetga chiqarishdan oldin production muhit/proksi sozlamalari bilan qayta tekshirish kerak. DEBUG=0 holatida kod secure cookie bayroqlarini yoqadi va alohida SECRET_KEY talab qiladi.

## Chegaralar va dalillar

Bu mavjud funksiyalarning auditidir; barcha ehtimoliy holatlar tekshirilganiga kafolat emas. Firefox/Safari, yuklama, parallel tahrirlash, tashqi server va HTTPS muhiti tekshirilmadi. Tibbiy ma’lumotlarning haqiqiyligi tekshirilmadi; katalogdagi 3 ta yozuv xayoliy namuna.

Brauzer natijalari: `/tmp/apteka-audit/results.json`. Skrinshotlar va sinov skriptlari: `/tmp/apteka-audit/`. Bu vaqtinchalik fayllar tizim tomonidan tozalanishi mumkin.
