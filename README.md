# Apteka — Django dori katalogi

Python 3.10+ va Django 5.2.17. SQLite bilan bitta aptekaning ichki katalogi.
Tarkib va qo‘llanish matni avtomatik yaratilmaydi. Ularni vakolatli xodim rasmiy
yo‘riqnoma asosida kiritadi. Matn kiritilganda manba va tekshirilgan sana majburiy.
Manbaning haqiqiyligini tekshirish xodim zimmasida; sayt tashqi manbani yuklamaydi.

> Yangilangan aniq lokal/server sozlamalari va backup/tiklash tartibi: [DEPLOYMENT.md](DEPLOYMENT.md).
> `DJANGO_SECRET_KEY` majburiy, `DJANGO_DEBUG` standart qiymati `0`. Lokal uchun `.env.example`dan foydalaning.

## Ishga tushirish

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# Faqat birinchi marta, .env mavjud bo‘lmasa:
(umask 077; cp -n .env.example .env)
python -c 'import secrets; from pathlib import Path; p=Path(".env"); p.write_text(p.read_text().replace("DJANGO_SECRET_KEY=\n", "DJANGO_SECRET_KEY=" + secrets.token_urlsafe(64) + "\n", 1))'
set -a
source .env
set +a
python scripts/compile_translations.py
python manage.py migrate
python manage.py setup_roles
python manage.py createsuperuser
python manage.py test
bash scripts/run_local.sh
```

Windows: `source .venv/bin/activate` o‘rniga `.venv\Scripts\activate`.
Sayt: http://127.0.0.1:8000/ — administrator: http://127.0.0.1:8000/admin/.
Boshlang‘ich migratsiya loyihaga qo‘shilgan. Model o‘zgarsa:
`python manage.py makemigrations catalog`, keyin `python manage.py migrate`.

## Xodimlar

Administrator (`is_superuser=True`) `/admin/` orqali xodim yaratadi. Yangi xodim
avtomatik **Aptekachi** guruhiga qo‘shiladi, `is_staff=False`, `is_superuser=False` bo‘ladi.
Faol aptekachi katalogni ko‘radi, qidiradi, o‘z smenasida sotadi va o‘z sotuvini bekor qiladi. Administrator katalog, dori
qo‘shish/tahrirlash, narx/qoldiq, admin orqali o‘chirish va xodimlarni boshqarishi mumkin.
Boshqaruv uchun `is_staff` yoki alohida permission yetarli emas: superuser talab qilinadi.
Eski `Vakolatli xodim` guruhi kirish yoki tahrirlash vakolatini bermaydi.
`setup_roles` takror ishlatilishi xavfsiz; mavjud foydalanuvchilarni o‘zgartirmaydi.

### Muhammad akkauntini o‘tkazish

Boshqa faol superuser hisobingiz borligini tekshiring, chunki bu amal Muhammadning
administrator vakolatini olib tashlaydi. Avval o‘zgarishni ko‘ring, keyin qo‘llang:

```bash
python manage.py setup_roles
python manage.py assign_aptekachi Muhammad
python manage.py assign_aptekachi Muhammad --apply
```

Nom registrga sezgir; hisob topilmasa buyruq xato bilan to‘xtaydi. Faqat ko‘rsatilgan
hisob guruhga qo‘shiladi va uning ikki bayrog‘i o‘chiriladi. Parol, boshqa profil
maydonlari va boshqa foydalanuvchilar o‘zgarmaydi. Buyruq takror ishlatilishi xavfsiz.

## Ishlash tartibi

- Qidiruv savdo nomi va faol moddalar bo‘yicha, 220 ms tanaffus bilan ishlaydi.
  JavaScript o‘chirilsa ham Qidirish tugmasi ishlaydi; bir sahifada 20 ta natija.
- Har bir joylashuvda bo‘lim, polka, qator va son saqlanadi. Jami qoldiq avtomatik hisoblanadi.
- Tahrirlash sahifasida “Yana joylashuv” bilan bir nechta joy qo‘shish mumkin.
  Joyni olib tashlash uchun o‘chirish belgisini qo‘yib saqlang. Kamida bitta joy kerak.
- Xayoliy namunalarda tarkib, qo‘llanish va rasmiy manba bo‘sh. Ular banner bilan ajratilgan.
  `seed_demo` takror ishga tushirilsa, mavjud namunalar o‘zgarmaydi.
- Tibbiy ma’lumot tekshirilgan sana alohida, yozuvning oxirgi yangilanish vaqti alohida saqlanadi.
- `search_text` oddiy `save()` orqali yangilanadi. Dorilarni `bulk_create` yoki
  `QuerySet.update()` bilan o‘zgartirmang: ular model validatsiyasi va qidiruv yangilanishini chetlab o‘tadi.

## Tekshiruv va chegaralar

`python manage.py test` qidiruv, sahifalash, Unicode, joylashuvlar, narx/qoldiqni
tahrirlash, tibbiy manba validatsiyasi, rollar, CSRF va HTML escapingni tekshiradi.
Interfeys mahalliy CSS/JS bilan ishlaydi; tashqi shrift yoki CDN talab qilinmaydi.

Bu dastlabki mahalliy SQLite loyiha. Ko‘p xodim bir vaqtda faol tahrirlasa PostgreSQL
va tahrirlar to‘qnashuvini aniqlash mexanizmini qo‘shish maqsadga muvofiq.
Internetga chiqarishda `DJANGO_DEBUG=0`, tasodifiy `DJANGO_SECRET_KEY`,
`DJANGO_ALLOWED_HOSTS`, HTTPS, WSGI server va static fayllarni xizmat qilishni sozlang;
`python manage.py collectstatic` va `python manage.py check --deploy`ni bajaring.
`runserver` mahalliy ishlab chiqish uchun.

### Aptekachi ish jarayoni

- Admin dori tahririda **Qadoq hajmi** va **Muqobil nomlar**ni kiritadi. Eski dorilarning qadoq hajmi taxmin qilinmaydi: bu maydon to‘ldirilmaguncha sotish bloklanadi. Qoldiq va narx birligi — pachka.
- Savdo nomi, faol modda va muqobil nom orqali lotin/kirillda qidiring. Aniq natija topilmasa, kichik imlo xatolari uchun ehtimoliy variantlar chiqadi. Dori avtomatik tanlanmaydi.
- **Smenalar → Smenani boshlash**, keyin dori sahifasida **Sotish**. Partiya, joy va miqdorni tanlab **Mahsulotni tekshirish**ni bosing. Alohida sahifadagi **Sotuvni tasdiqlash**gina qoldiqni kamaytiradi. Tasdiq 15 daqiqa amal qiladi; narx, mahsulot, partiya, joy va qoldiq qayta tekshiriladi.
- Natija kartasi yoki dori sahifasidagi **Qayerda turibdi?** mavjud partiya/joylarning qoldig‘ini ko‘rsatadi. Nol qoldiq chiqarilmaydi.
- **Smenalar**da aptekachi faqat o‘z smenalarini, admin barchasini ko‘radi. Smena hisobotida sotuvlar, pachkalar va summa bor. Sotuv bekor qilinsa qoldiq bir marta qaytariladi, tushumdan chiqariladi va tarix saqlanadi.
- Admin **Boshqaruv → Batch → Add** orqali partiya yaratib, dori tahririda joylashuvga bog‘laydi. **Polkalar orasida ko‘chirish** sahifasida manba partiya/joy, yangi bo‘lim/polka/qator va miqdorni kiriting. Tarix shu sahifada ko‘rinadi; umumiy qoldiq o‘zgarmaydi.

Migratsiyalar eski dorilar va joylashuvlarning ID hamda qoldiqlarini saqlab, ularni **Boshlang‘ich partiya**ga bog‘laydi. Oldingi loyihada sotuv yoki smena modeli bo‘lmagan. Tarixga bog‘langan yozuvlarni o‘chirish himoyalangan; tarix admin panelida faqat o‘qiladi.

Tekshirish: `.venv/bin/python manage.py test` va `.venv/bin/python manage.py makemigrations --check --dry-run`.


### Xodimlar jadvali

Admin **Smenalar → Ish jadvalini belgilash** orqali aptekachi, boshlanish va tugash sanasi/vaqtini belgilaydi (Toshkent vaqti). Bir xodimning rejalari ustma-ust kelmaydi; tungi smenada tugash sanasi keyingi kun bo‘lishi mumkin.

Aptekachi o‘z rejasidagi **Smenani boshlash** tugmasini, ish tugagach **Smenani yakunlash** tugmasini bosadi. Reja va haqiqiy vaqt alohida saqlanadi. Jadvaldan tashqari smena boshlash ham mavjud. Admin barcha xodimlarning rejalari, haqiqiy vaqtlari, ishlagan davomiyligi va smena bo‘yicha sotuvlar/pachkalar/summani ko‘radi; aptekachi faqat o‘z ma’lumotlarini ko‘radi. Bekor qilingan sotuvlar natijalarga qo‘shilmaydi.

### Apteka egasining kundalik paneli

`/admin/` — apteka egasining yagona boshqaruv paneli, faqat faol `is_superuser=True` foydalanuvchi uchun. Sayt menyusidagi **Admin panel** havolasi faqat adminga ko‘rinadi. Oddiy aptekachi, hatto `is_staff=True` bo‘lsa ham, admin sahifalariga GET/POST so‘rovlarida 403 oladi. Eski alohida boshqaruv manzili olib tashlangan (404).

Panel bugungi bekor qilinmagan sotuvlar soni, pachkalar va tushumni Toshkent sanasi bo‘yicha hisoblaydi. Kam qoldiq barcha joylashuvlar yig‘indisidan olinadi. Yaroqlilik ogohlantirishlari faqat qoldig‘i bor partiyalar uchun: bugundan oldingi sanalar muddati o‘tgan, bugungi sana esa yaqinlashayotgan guruhga kiradi. Sana kiritilmagan partiyalar soni ham ko‘rsatiladi. Bugungi eng ko‘p sotilgan 5 dori pachkalar bo‘yicha, oxirgi 10 sotuv esa barcha kunlar bo‘yicha ko‘rsatiladi.

Chegaralar `config/settings.py` yoki muhit o‘zgaruvchilarida belgilanadi:
- `PHARMACY_LOW_STOCK_THRESHOLD=10`: jami qoldig‘i 10 pachkadan **kam** dorilar.
- `PHARMACY_EXPIRY_WARNING_DAYS=30`: bugundan keyingi 30 kun ichida muddati tugaydigan partiyalar.

Paneldagi dorilar, partiyalar, xodimlar, smenalar va hisobotlar tugmalari mavjud Django admin sahifalariga olib boradi. Dori va partiya qo‘shish hamda tahrirlash imkoniyatlari saqlangan. Hisobotlar sana va xodim bo‘yicha filtrlanadi. Smena jadvalini belgilash sayt menyusidagi Smenalar sahifasida mavjud. Ma’lumotlar bazasi tuzilishi o‘zgarmaydi, migratsiya talab qilinmaydi.

Tekshiruv: muhit sozlangach `.venv/bin/python manage.py test`. Panel testlari: `catalog/test_dashboard.py`.
