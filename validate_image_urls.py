"""
Проверка URL картинок в БД. Показывает, какие работают, какие нет.
Запуск: python validate_image_urls.py
Требует: DATABASE_URL
"""
import os
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_PRIVATE_URL')
if not DATABASE_URL:
    print("❌ Задайте DATABASE_URL")
    exit(1)
if 'sslmode=' not in DATABASE_URL and 'rlwy.net' in DATABASE_URL:
    DATABASE_URL += ('&' if '?' in DATABASE_URL else '?') + 'sslmode=require'

def is_image(data):
    if not data or len(data) < 4:
        return False
    d = data[:12]
    return (d[:2] == b'\xff\xd8' or d[:8] == b'\x89PNG\r\n\x1a\n' or
            d[:6] in (b'GIF87a', b'GIF89a') or (d[:4] == b'RIFF' and d[8:12] == b'WEBP'))

def check_url(url):
    try:
        r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}"
        if not is_image(r.content):
            return False, "не изображение"
        return True, "OK"
    except Exception as e:
        return False, str(e)[:50]

conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
cur = conn.cursor()
cur.execute("SELECT id, exercise_name, image_start_url, image_finish_url FROM exercises ORDER BY id")
rows = cur.fetchall()
conn.close()

ok_start = ok_finish = fail_start = fail_finish = 0
print("=" * 70)
print("ПРОВЕРКА URL КАРТИНОК")
print("=" * 70)
fails = []
for r in rows:
    name = (r['exercise_name'] or '')[:35]
    s_url = (r['image_start_url'] or '').strip()
    f_url = (r['image_finish_url'] or '').strip()
    s_ok, s_err = check_url(s_url) if s_url.startswith('http') else (False, "нет URL")
    f_ok, f_err = check_url(f_url) if f_url.startswith('http') else (False, "нет URL")
    if s_ok: ok_start += 1
    else: fail_start += 1
    if f_ok: ok_finish += 1
    else: fail_finish += 1
    if not s_ok or not f_ok:
        fails.append((r['id'], name, s_ok, s_err, f_ok, f_err, s_url[:60], f_url[:60]))

print(f"\n✅ image_start: {ok_start} OK, {fail_start} fail")
print(f"✅ image_finish: {ok_finish} OK, {fail_finish} fail")
if fails:
    print("\n⚠️ Упражнения с битыми URL:")
    for id_, name, s_ok, s_err, f_ok, f_err, su, fu in fails[:20]:
        status = []
        if not s_ok: status.append(f"start: {s_err}")
        if not f_ok: status.append(f"finish: {f_err}")
        print(f"  {id_} {name}: {', '.join(status)}")
        if not s_ok and su: print(f"      start: {su}")
        if not f_ok and fu: print(f"      finish: {fu}")
    if len(fails) > 20:
        print(f"  ... и ещё {len(fails)-20}")
print("\n✅ Готово")
