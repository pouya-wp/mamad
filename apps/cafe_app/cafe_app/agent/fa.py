"""Persian text helpers shared by the agent."""

import re

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
_TO_LATIN = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
WEEKDAYS = ("دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه")


def fa(number, digits=0):
	text = f"{number or 0:,.{digits}f}".replace(",", "٬")
	return text.translate(_FA_DIGITS)


def toman(rial):
	return fa(round((rial or 0) / 10))


def percent(value, signed=False):
	"""Unsigned by default, for sentences that already say "more"/"less"."""
	number = value or 0
	text = f"{fa(abs(number))}٪"
	return f"−{text}" if signed and number < 0 else text


def normalize(text):
	"""Latin digits, Persian ی/ک, no thousands separators, single spaces."""
	text = (text or "").translate(_TO_LATIN).replace("ي", "ی").replace("ك", "ک")
	text = re.sub(r"(?<=\d)[٬,](?=\d{3})", "", text)
	return re.sub(r"\s+", " ", text).strip()
