# راه‌اندازی ERPNext + cafe_app روی VPS

## ۱. مشخصات VPS
| | حداقل | پیشنهادی |
|---|---|---|
| سیستم‌عامل | Ubuntu 24.04 LTS | Ubuntu 24.04 LTS |
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| دیسک | 40 GB SSD | 80 GB SSD |

> ⚠️ اگه VPS داخل ایرانه، دسترسی به Docker Hub و GitHub ممکنه محدود باشه. قبل از خرید از فروشنده بپرس **Docker registry mirror** دارن یا نه، وگرنه `docker pull` کار نمی‌کنه.

## ۲. تست سریع (فقط خود ERPNext، بدون cafe_app)
```bash
curl -fsSL https://get.docker.com | bash
git clone --depth 1 https://github.com/frappe/frappe_docker
cd frappe_docker
docker compose -f pwd.yml up -d
docker compose -f pwd.yml logs -f create-site   # صبر تا ساخت سایت تموم بشه
```
آدرس: `http://IP-سرور:8080` — نام کاربری `Administrator`، رمز `admin` (بلافاصله عوضش کن).

## ۳. نسخه‌ی اصلی با cafe_app
1. `apps/cafe_app` رو توی یک ریپوی **خصوصی** GitHub پوش کن.
2. روی سرور فایل `apps.json` بساز:
```json
[
  { "url": "https://github.com/frappe/erpnext", "branch": "version-16" },
  { "url": "https://<TOKEN>@github.com/<user>/cafe_app", "branch": "main" }
]
```
3. ساخت image اختصاصی:
```bash
docker build --build-arg=FRAPPE_BRANCH=version-16 \
  --secret=id=apps_json,src=apps.json \
  --tag=cafe-erp:16 --file=images/layered/Containerfile .
```
4. فایل env (رمزها رو عوض کن):
```bash
cp example.env cafe.env
# داخل cafe.env: DB_PASSWORD=رمز-قوی ، CUSTOM_IMAGE=cafe-erp ، CUSTOM_TAG=16 ، PULL_POLICY=never
```
5. ساخت compose و اجرا:
```bash
docker compose --env-file cafe.env -f compose.yaml \
  -f overrides/compose.mariadb.yaml -f overrides/compose.redis.yaml \
  -f overrides/compose.noproxy.yaml config > compose.cafe.yaml
docker compose -p cafe -f compose.cafe.yaml up -d
```
6. ساخت سایت هر کافه (هر کافه = یک سایت و دیتابیس جدا):
```bash
docker compose -p cafe exec backend bench new-site cafe1.example.com \
  --mariadb-user-host-login-scope=% --db-root-password <DB_PASSWORD> \
  --admin-password <رمز-ادمین> --install-app erpnext --install-app cafe_app
```

برای دامنه و SSL: `frappe_docker/docs/03-production/01-tls-ssl-setup.md`
