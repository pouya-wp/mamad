"""Proactive observations the agent surfaces on the dashboard, computed from live data."""

from frappe.utils import add_days, getdate, nowdate, nowtime

from cafe_app.agent.fa import WEEKDAYS, fa, percent, toman
from cafe_app.api import accounting, dashboard
from cafe_app.utils import get_cafe_settings


def daily_insights():
	company = get_cafe_settings().company
	today = getdate(nowdate())
	insights = []

	# Today so far vs the same weekday last week, up to the same hour
	now = dashboard._sales_kpis(company, today, today)
	last_week_day = add_days(today, -7)
	last_week = dashboard._sales_kpis(company, last_week_day, last_week_day, nowtime())
	if now["revenue"] and last_week["revenue"]:
		change = (now["revenue"] - last_week["revenue"]) / last_week["revenue"] * 100
		insights.append(
			{
				"tone": "up" if change >= 0 else "down",
				"text": f"فروش امروز تا الان {toman(now['revenue'])} تومانه؛ {percent(change)} {'بیشتر' if change >= 0 else 'کمتر'} از {WEEKDAYS[today.weekday()]} هفته قبل تا همین ساعت.",
				"ask": "فروش امروز چطور بود؟",
			}
		)

	# Stock running out
	low = dashboard.low_stock()
	if low:
		names = "، ".join(r.item_name for r in low[:3])
		insights.append(
			{
				"tone": "warn",
				"text": f"{fa(len(low))} قلم رو به اتمامه ({names}). بهتره امروز سفارش بدی.",
				"ask": "چی داره تموم میشه؟",
			}
		)

	# Peak hour of the last 7 days
	hours = dashboard._hourly(company, add_days(today, -6), today)
	peak = max(hours, key=lambda h: h["orders"])
	if peak["orders"]:
		insights.append(
			{
				"tone": "info",
				"text": f"شلوغ‌ترین ساعت هفته {fa(peak['hour'])} تا {fa(peak['hour'] + 1)} بوده؛ برای این ساعت نیروی بیشتری بذار.",
				"ask": "پرفروش‌های این هفته",
			}
		)

	# Month profitability
	report = accounting.overview("month")
	if report["income"]:
		margin = report["net_profit"] / report["income"] * 100
		insights.append(
			{
				"tone": "up" if margin >= 15 else "down",
				"text": f"حاشیه سود خالص ۳۰ روز اخیر {percent(margin, signed=True)} بوده ({toman(report['net_profit'])} تومان).",
				"ask": "سود و زیان این ماه",
			}
		)

	return insights
