"""Jalali (Shamsi) to Gregorian conversion for dates the café writes by hand."""

import datetime
import re

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def to_gregorian(jy, jm, jd):
	jy += 1595
	days = -355668 + 365 * jy + (jy // 33) * 8 + ((jy % 33) + 3) // 4 + jd
	days += (jm - 1) * 31 if jm < 7 else (jm - 7) * 30 + 186
	gy = 400 * (days // 146097)
	days %= 146097
	if days > 36524:
		days -= 1
		gy += 100 * (days // 36524)
		days %= 36524
		if days >= 365:
			days += 1
	gy += 4 * (days // 1461)
	days %= 1461
	if days > 365:
		gy += (days - 1) // 365
		days = (days - 1) % 365
	gd = days + 1
	leap = (gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0
	months = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
	gm = 0
	while gm < 12 and gd > months[gm]:
		gd -= months[gm]
		gm += 1
	return datetime.date(gy, gm + 1, gd)


def from_gregorian(date):
	"""date -> (jy, jm, jd)."""
	gy, gm, gd = date.year, date.month, date.day
	g_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
	gy2 = gy + 1 if gm > 2 else gy
	days = 355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 + gd + g_days[gm - 1]
	jy = -1595 + 33 * (days // 12053)
	days %= 12053
	jy += 4 * (days // 1461)
	days %= 1461
	if days > 365:
		jy += (days - 1) // 365
		days = (days - 1) % 365
	if days < 186:
		return jy, 1 + days // 31, 1 + days % 31
	return jy, 7 + (days - 186) // 30, 1 + (days - 186) % 30


def parse(text):
	"""'1405/06/23' (Persian or Latin digits) -> date; None when empty or malformed."""
	if not text:
		return None
	match = re.fullmatch(r"\s*(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})\s*", str(text).translate(_DIGITS))
	if not match:
		return None
	jy, jm, jd = map(int, match.groups())
	if not (1 <= jm <= 12 and 1 <= jd <= 31):
		return None
	return to_gregorian(jy, jm, jd)
