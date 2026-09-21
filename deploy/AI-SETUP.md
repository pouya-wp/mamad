# اتصال دستیار One به OpenAI یا DeepSeek

دستیار بدون تنظیمات در **حالت دمو** کار می‌کند: یک موتور فارسی داخلی که سؤال‌های رایج (فروش، سود و زیان، موجودی، پرفروش‌ها، موجودی صندوق) را با داده‌های واقعی جواب می‌دهد و هزینه/خرید/ضایعات را از یک جمله پیشنهاد می‌دهد.

با اضافه کردن سه مقدار به `site_config.json` سایت، دستیار به مدل زبانی واقعی وصل می‌شود (هر API سازگار با OpenAI Chat Completions):

| کلید | DeepSeek | OpenAI |
|---|---|---|
| `ai_base_url` | `https://api.deepseek.com` | `https://api.openai.com/v1` |
| `ai_model` | نام مدل از پنل DeepSeek | نام مدل از پنل OpenAI |
| `ai_api_key` | کلید API | کلید API |

```bash
docker compose exec backend bench --site <site> set-config ai_base_url "https://api.deepseek.com"
docker compose exec backend bench --site <site> set-config ai_model "<model>"
docker compose exec backend bench --site <site> set-config ai_api_key "<key>"
```

- کلید فقط سمت سرور می‌ماند و هیچ‌وقت به مرورگر نمی‌رسد.
- ابزارهای ایجنت در `apps/cafe_app/cafe_app/agent/tools.py` تعریف شده‌اند؛ هر ابزار نوشتنی (هزینه، خرید، ضایعات) فقط **پیشنهاد** می‌سازد و سند بعد از تأیید کاربر در پنل ثبت می‌شود.
- ⚠️ اگر سرور در ایران است، دسترسی به API این سرویس‌ها ممکن است بسته باشد؛ از پراکسی یا سرور خارج استفاده کنید.
