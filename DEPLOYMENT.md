# Lokal ishga tushirish va serverga joylash

## Lokal

Loyiha papkasida (Python 3.10+):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Mavjud .env va kalit saqlanadi:
(umask 077; cp -n .env.example .env)
python -c 'import secrets; from pathlib import Path; p=Path(".env"); p.write_text(p.read_text().replace("DJANGO_SECRET_KEY=\n", "DJANGO_SECRET_KEY=" + secrets.token_urlsafe(64) + "\n", 1))'
chmod 600 .env
set -a
source .env
set +a
python scripts/compile_translations.py
python manage.py migrate
python manage.py setup_roles
python manage.py test --noinput
bash scripts/run_local.sh
```

Mavjud `.env` bo‘lsa, uning ustiga nusxalamang, mavjud kalitni saqlang.
Keyingi ishga tushirishlarda loyiha papkasida faqat `bash scripts/run_local.sh`
yozing: skript `.env`ni yuklaydi va serverni `127.0.0.1:8000`da ochadi.
Oddiy `manage.py` buyruqlari `.env`ni avtomatik yuklamaydi: ular uchun har yangi
terminalda `set -a; source .env; set +a` bajaring.
Lokal `DJANGO_DEBUG=1` HTTPS redirect, HSTS va secure cookie talabini o‘chiradi.
Productionda `DJANGO_DEBUG=0` (standart) ularni qayta yoqadi; lokal skriptni ishlatmang.
`.env` Gitdan chiqarilgan va `600` huquq bilan faqat egasiga ochiq bo‘lishi kerak.
Brauzer oldingi HTTPS redirectni eslab qolsa, `http://127.0.0.1:8000/`ni
maxfiy oynada oching yoki shu manzil uchun brauzer keshini tozalang.
Yangi bazada `python manage.py createsuperuser`; mavjud hisoblarni almashtirmang.
http://127.0.0.1:8000/ va /admin/. Ishchi bazada `seed_demo` talab qilinmaydi.

Admin: Dorilar → dori/narx/qadoq/tarkib/qo‘llanish va joylashuv;
Partiyalar → dori/partiya raqami/yaroqlilik sanasi; keyin dori joylashuvini o‘sha
partiyaga bog‘lang. Narx bir pachka uchun, dori darajasida: uning barcha partiyalarida
bir xil. Har bir joylashuvdagi son alohida hisoblanadi. Sana noma’lum partiyalar
saqlanadi, sotuvdan oldin sana kiritilishi kerak. Bugungi sana amal qiladi;
bugundan oldingi sana bloklanadi. Xodim: smenani boshlash → qidirish → sotish →
partiya va pachka soni → tekshirish → tasdiqlash. Bekor qilish tarixi o‘chirilmaydi.

## Server (Linux, HTTPS, Nginx, Gunicorn)

1. Dastur va `.venv`ni masalan `/srv/apteka`ga joylang. Alohida tizim foydalanuvchisi
   `apteka` yarating; shu foydalanuvchiga loyiha va SQLite papkasiga yozish huquqi bering.
   Mavjud bazani ko‘chirishdan oldin quyidagi backupni oling. Bo‘sh bazaga almashtirmang.
2. `pip install -r requirements.txt`, keyin `pip install gunicorn`.
   PostgreSQL tanlansa `pip install 'psycopg[binary]>=3.1.8,<4'` ham kerak.
3. `/etc/apteka.env` (egasi servis foydalanuvchisi, 600 huquq) ichida yangi tasodifiy
   kalit, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS=haqiqiy.domen.uz`,
   `DJANGO_CSRF_TRUSTED_ORIGINS=https://haqiqiy.domen.uz`, `DJANGO_TRUST_PROXY=1` belgilang.
   Kalitni `python -c 'import secrets; print(secrets.token_urlsafe(64))'` bilan yarating;
   Gitga yubormang. Barcha workerlar bir xil kalit ishlatsin.
4. SQLite saqlansa `SQLITE_PATH=/srv/apteka/db.sqlite3`. Bir server va mahalliy diskda
   ishlating. IMMEDIATE tranzaksiya yozuvlarni navbatlaydi, kutish 20 soniya.
   Katta yuklama/ko‘p server uchun PostgreSQL: `DB_ENGINE=postgresql`, `DB_NAME`,
   `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`ni belgilang. Bo‘sh PostgreSQLga
   o‘tish SQLite ma’lumotlarini avtomatik ko‘chirmaydi; pastdagi tartibni bajaring.
5. Servis muhitini yuklab quyidagilarni bajaring:

```bash
set -a
source /etc/apteka.env
set +a
.venv/bin/python scripts/compile_translations.py
.venv/bin/python manage.py migrate
.venv/bin/python manage.py setup_roles
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check --deploy
```

6. `/etc/systemd/system/apteka.service`:

```ini
[Unit]
Description=Apteka Django
After=network.target
[Service]
User=apteka
Group=apteka
WorkingDirectory=/srv/apteka
EnvironmentFile=/etc/apteka.env
ExecStart=/srv/apteka/.venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2 --access-logfile - --error-logfile -
Restart=on-failure
[Install]
WantedBy=multi-user.target
```

7. Domen DNSini serverga yo‘naltiring, haqiqiy TLS sertifikat oling. Nginx HTTPS
   server blokida (sertifikat yo‘llarini o‘zingiznikiga almashtiring):

```nginx
server {
    listen 80;
    server_name haqiqiy.domen.uz;
    return 301 https://$host$request_uri;
}
server {
    listen 443 ssl;
    server_name haqiqiy.domen.uz;
    ssl_certificate /etc/letsencrypt/live/haqiqiy.domen.uz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/haqiqiy.domen.uz/privkey.pem;
    location /static/ { alias /srv/apteka/staticfiles/; }
    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://127.0.0.1:8000;
    }
}
```

Nginx noma’lum domenlar uchun default blokda so‘rovni rad etsin.
Gunicorn portini internetga ochmang; `DJANGO_TRUST_PROXY=1` faqat yuqoridagi kabi
sarlavhani qayta yozadigan ishonchli proksi bilan. HSTS subdomenlar uchun ham yoqilgan;
ular ham HTTPS xizmat qilsin. `sudo nginx -t`, `sudo systemctl reload nginx`,
`sudo systemctl daemon-reload`, `sudo systemctl enable --now apteka`.
`journalctl -u apteka` orqali logni kuzating. Domen orqali kirish, statik fayllar,
ikkala til, bitta test sotuv/bekor qilishni tekshiring.

## Backup va tiklash

SQLite uchun ishlayotgan bazadan izchil nusxa (mavjud fayl ustiga yozmaydi):

```bash
python manage.py backup_sqlite /xavfsiz/backup/apteka-2026-09-25.sqlite3
```

Papka avval yaratilgan va servis foydalanuvchisiga ochiq bo‘lsin. Kunlik cron/systemd
timerda sanali noyob nom ishlating. Nusxani shifrlangan boshqa server/diskka ham
ko‘chiring, masalan 30 kunlik nusxalarni saqlang. `.env`/server kalitlari alohida
himoyalangan backupda bo‘lsin. Nusxalarni statik/web papkasiga qo‘ymang.
Tiklash: servisni to‘xtating, joriy bazani alohida saqlang, tanlangan backupni
`SQLITE_PATH`ga nusxalang, egasi/huquqlarini tiklang, `migrate` va `check` bajaring,
servisni ishga tushiring. Avval alohida muhitda tiklashni mashq qiling.

PostgreSQL: maxfiy ulanish ma’lumotlarini `.pgpass` (600) yoki himoyalangan servis
muhitida saqlang. `pg_dump -Fc -h 127.0.0.1 -U apteka apteka -f backup.dump`.
Tiklashni yangi bazada `pg_restore --no-owner -h 127.0.0.1 -U apteka -d apteka_restore backup.dump`
bilan sinang; tekshiruvdan keyingina servis ulanishini almashtiring.

SQLite → PostgreSQL ko‘chirish: sotuv/yozuvlarni to‘xtating, backup oling; SQLite
muhitida `python manage.py dumpdata --natural-foreign --natural-primary --exclude
contenttypes --exclude auth.permission --indent 2 --output /xavfsiz/backup/data.json`
(buyruqni bir qatorda yozing). PostgreSQL uchun yangi bo‘sh bazada `migrate`, keyin
`loaddata /xavfsiz/backup/data.json`. Dori, partiya, joylashuv, sotuv, smena sonlari va
jami qoldiq/tushumni solishtiring, testlarni alohida test bazasida bajaring.
SQLite asl nusxasini saqlang; import tasdiqlanmaguncha savdoni ochmang.

Manbalar: [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/),
[Django SQLite transaction modes](https://docs.djangoproject.com/en/5.2/ref/databases/#sqlite-notes).

## 2026-09-25 tekshiruvi va yangilash

- `DB_ENGINE` faqat `sqlite` yoki `postgresql` qabul qiladi. Noto‘g‘ri yozilgan
  qiymat bilan dastur ishga tushmaydi; tasodifan boshqa bo‘sh bazaga ulanmaydi.
- Qoldiq tahririda yashirin imzolangan holat yuboriladi. Forma ochilgandan keyin
  sotuv, bekor qilish yoki ko‘chirish bo‘lsa, eski forma saqlanmaydi. Sahifani
  yangilab, joriy sonni tekshirib qayta kiriting. Yangilanishdan oldin ochilgan
  tahrir sahifalarini ham qayta yuklang.
- Ushbu yangilanish uchun yangi migratsiya kerak emas. `makemigrations --check
  --dry-run` o‘tdi; mavjud bazada barcha 7 ta catalog migratsiyasi qo‘llangan.
- 70 ta Django testi va bitta Chromium ish jarayoni testi SQLite’da o‘tdi.
  PostgreSQL’da testlar alohida bajarilishi kerak; undagi test foydalanuvchisiga
  test bazasini yaratish huquqi kerak.
- Ixtiyoriy brauzer tekshiruvi: `pip install playwright`, Chromium/Chrome o‘rnatib,
  `DJANGO_DEBUG=1 python scripts/browser_workflow.py`. Skript hozir
  `/usr/bin/google-chrome`dan foydalanadi va alohida test bazasi yaratadi.
- `check --deploy` ishlab chiqarish parametrlariga o‘xshash muhitda xatosiz o‘tdi.
  Bu haqiqiy domen, TLS sertifikati yoki server o‘rnatilganini anglatmaydi.

Batafsil tekshiruv: [reports/readiness-review-2026-09-25.md](reports/readiness-review-2026-09-25.md).
