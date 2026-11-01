# اتصال دستیار One به OpenAI

کلید API فقط در `site_config.json` سرور ذخیره می‌شود و به اپ ویندوز یا مرورگر نمی‌رود. در ۲۷ سپتامبر ۲۰۲۶، پس از اجازهٔ کاربر `ai_enabled=1` شد و یک گفت‌وگوی زندهٔ احرازهویت‌شده با موفقیت پاسخ گرفت.

مدل پیش‌فرض عملیاتی `gpt-6-luna` است. در Chat Completions برای استفاده از ابزارهای این مدل باید `reasoning_effort` روی `none` باشد. کد همین تنظیم را برای این مدل اعمال می‌کند.

## تنظیم روی سرور

داخل کانتینر backend:

```bash
bench --site frontend set-config ai_base_url https://api.openai.com/v1
bench --site frontend set-config ai_model gpt-6-luna
bench --site frontend set-config ai_daily_token_limit 300000
bench --site frontend set-config ai_max_completion_tokens 800
bench --site frontend set-config ai_max_input_bytes 12000
bench --site frontend set-config ai_max_steps 3
bench --site frontend set-config ai_enabled 1
```

کلید را با روش امنی که در خط فرمان history یا لاگ ضبط نشود در `ai_api_key` سایت وارد کنید و backend را restart کنید. کلید را در ریپو، فایل نصب ویندوز، یا URL قرار ندهید. `ai_enabled=1` پس از مجوز صریح برای ارسال داده‌های کافه به OpenAI فعال شده است.

برای سقف مستقل از برنامه، در تنظیمات همان پروژهٔ OpenAI یک **hard spend limit** ماهانه نیز تنظیم کنید؛ هشدار هزینه به‌تنهایی درخواست‌ها را متوقف نمی‌کند. مستندات رسمی: https://developers.openai.com/api/docs/guides/spend-limits

## سقف مصرف داخل برنامه

- حداکثر ۸۰۰ توکن خروجی در هر درخواست مدل.
- حداکثر ۳ درخواست مدل در هر گفت‌وگو و حداکثر ۱۲٬۰۰۰ بایت ورودی در هر درخواست.
- حداکثر ۳۰۰٬۰۰۰ توکن رزروشده در روز برای کل سایت. قبل از هر درخواست، مقدار محافظه‌کارانه‌ای بر اساس بایت‌های ورودی و سقف خروجی در Redis به‌صورت اتمیک رزرو می‌شود. اگر Redis در دسترس نباشد، درخواست مدل فرستاده نمی‌شود. رزروهای ناموفق پس داده نمی‌شوند؛ بنابراین سقف ممکن است زودتر از مصرف واقعی پر شود.
- پیشنهادهای هزینه، خرید و ضایعات فقط پس از تأیید کاربر ثبت می‌شوند.

این سقف فقط ترافیک همین برنامه را پوشش می‌دهد؛ برای پوشش سایر استفاده‌ها از کلید یا پروژه، hard spend limit در OpenAI هم لازم است. این سقف بیرونی هنوز در حساب OpenAI تنظیم نشده است؛ پاسخ واقعی مدل و اتصال سرور به API تأیید شده‌اند.
