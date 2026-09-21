# ONE CAFE — پنل مدیریت کافه

پنل اختصاصی کافهٔ [ONE](https://www.instagram.com/one1cafe) در یزد: صندوق، انبار، خرید، حسابداری و یک دستیار هوش مصنوعی که گزارش‌ها و اسناد را مثل رسید چاپ می‌کند.

پنل یک اپ جدا (Vue 3 + Vite) است که فقط از طریق API به بک‌اند ERPNext وصل می‌شود، و یک نسخهٔ نمایشی هم دارد که بدون هیچ بک‌اندی روی Vercel بالا می‌آید.

```
panel/            اپ پنل (Vue 3 + Vite + Tailwind v4)
  src/demo/       کافهٔ ساختگی برای نسخهٔ نمایشی (بدون بک‌اند)
apps/cafe_app/    اپ Frappe: API‌ها، دستیار، راه‌اندازی کافه
deploy/           راه‌اندازی لوکال، VPS و تنظیم مدل هوش مصنوعی
docs/             ایده‌های در صف
```

## نسخهٔ نمایشی (Vercel)

نسخهٔ نمایشی هیچ بک‌اندی ندارد: کل کافه — شش ماه سفارش، خرید، هزینه و شیفت — از روی منو و رسپی واقعی، داخل مرورگر ساخته می‌شود (`panel/src/demo`). لاگین هم ندارد و مستقیم وارد داشبورد می‌شود. فروش در صندوق، ثبت ضایعات، تأیید فیش‌های دستیار و حتی ضربان زندهٔ کافه، همه کار می‌کنند و همان دادهٔ داخل مرورگر را تغییر می‌دهند.

در Vercel:

1. مخزن را import کن.
2. **Root Directory** را روی `panel` بگذار.
3. بقیه‌اش خودکار است (`panel/vercel.json` دستور build و مسیر SPA را دارد).

اجرای همین نسخه روی سیستم خودت:

```bash
cd panel
npm install
npm run dev:demo      # نسخهٔ نمایشی، بدون بک‌اند
npm run build:demo    # خروجی production همان نسخه
```

## نسخهٔ واقعی (با ERPNext)

```bash
cd panel
npm install
npm run dev           # به http://localhost:8080 پراکسی می‌شود
```

راه‌اندازی بک‌اند در [`deploy/LOCAL-SETUP.md`](deploy/LOCAL-SETUP.md)، استقرار روی سرور در [`deploy/VPS-SETUP.md`](deploy/VPS-SETUP.md) و اتصال مدل هوش مصنوعی در [`deploy/AI-SETUP.md`](deploy/AI-SETUP.md) توضیح داده شده.
