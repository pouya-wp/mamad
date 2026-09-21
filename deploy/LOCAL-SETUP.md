# اجرای ERPNext روی لپ‌تاپ (WSL + Docker)

> ⚠️ **Hiddify باید روشن باشه** (حالت TUN)، وگرنه Docker به Docker Hub وصل نمیشه.

## روشن کردن
```bash
wsl -d Ubuntu-24.04 -- docker compose -f /mnt/c/Users/Pouya/Desktop/PROJECTS/mamad/frappe_docker/pwd.yml -f /mnt/c/Users/Pouya/Desktop/PROJECTS/mamad/deploy/compose.cafe-dev.yaml up -d
```
فایل `deploy/compose.cafe-dev.yaml` پوشه‌ی `apps/cafe_app` رو مستقیم به کانتینرها وصل می‌کنه، پس تغییرات کد بلافاصله داخل کانتینرها هم هست.
برای اعمال تغییرات پایتون، کانتینرها رو ری‌استارت کن:
```bash
wsl -d Ubuntu-24.04 -- docker compose -f /mnt/c/Users/Pouya/Desktop/PROJECTS/mamad/frappe_docker/pwd.yml -f /mnt/c/Users/Pouya/Desktop/PROJECTS/mamad/deploy/compose.cafe-dev.yaml restart backend queue-long queue-short scheduler
```
و بعد از تغییر DocTypeها:
```bash
wsl -d Ubuntu-24.04 -- docker compose -f /mnt/c/Users/Pouya/Desktop/PROJECTS/mamad/frappe_docker/pwd.yml exec backend bench --site frontend migrate
```
بعد برو: **http://localhost:8080**
- نام کاربری: `Administrator`
- رمز: `admin` ← بعد از اولین ورود عوضش کن

## خاموش کردن (داده‌ها می‌مونن)
```bash
wsl -d Ubuntu-24.04 -- docker compose -f /mnt/c/Users/Pouya/Desktop/PROJECTS/mamad/frappe_docker/pwd.yml stop
```
برای آزاد کردن کامل رم ویندوز:
```bash
wsl --shutdown
```

## وضعیت کانتینرها
```bash
wsl -d Ubuntu-24.04 -- docker compose -f /mnt/c/Users/Pouya/Desktop/PROJECTS/mamad/frappe_docker/pwd.yml ps
```

## تنظیماتی که روی سیستم انجام شده
| چی | کجا | چرا |
|---|---|---|
| سقف رم ۵ گیگ + swap ۴ گیگ | `C:\Users\Pouya\.wslconfig` | ویندوز هنگ نکنه |
| `networkingMode=mirrored` | `.wslconfig` | ترافیک WSL از Hiddify رد بشه |
| `instanceIdleTimeout=-1` و `vmIdleTimeout=-1` | `.wslconfig` | WSL وسط کار Docker خودش خاموش نشه |
| سرویس `wsl-mtu-fix` (MTU=1400) | داخل Ubuntu، فایلش: `deploy/wsl-mtu-fix.service` | با MTU پیش‌فرض 9000 همه‌ی اتصال‌های HTTPS گیر می‌کردن |
| Docker Engine از مخزن `download.docker.com` | داخل Ubuntu | `get.docker.com` مسدوده |
