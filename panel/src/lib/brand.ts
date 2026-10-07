/**
 * Whose café this panel belongs to. The real build is ONE CAFE's own panel; the
 * demo build wears an invented café instead, so screenshots and marketing content
 * can be made freely without putting a real shop's numbers on display.
 */
export type Brand = {
  /** Persian name, the way staff say it */
  name: string
  /** Latin name for the mark and the receipts */
  latin: string
  /** the letter printed in the café's orange */
  accent: string
  /** letterspaced line under the mark */
  wordmark: string
  /** what the assistant is called */
  assistant: string
  city: string
  cityLatin: string
  address: string
  hours: string
  /** printed at the foot of a story card; never a real social handle */
  handle: string
  taglineLatin: string
  taglineFa: string
}

const ONE_CAFE: Brand = {
  name: 'ONE CAFE',
  latin: 'ONE',
  accent: 'O',
  wordmark: 'ONE CAFE',
  assistant: 'دستیار One',
  city: 'یزد',
  cityLatin: 'YAZD',
  address: 'یزد · بلوار دانشگاه · کوچه فرساد',
  hours: 'هر روز ۸:۳۰ تا ۲۳:۳۰',
  handle: '@one1cafe',
  taglineLatin: 'ONE GOOD COFFEE, ONE GOOD CAFE',
  taglineFa: 'یک قهوهٔ خوب، یک کافهٔ خوب',
}

/** Invented from scratch: a café that does not exist, named after the citrus. */
const TORANJ: Brand = {
  name: 'کافه ترنج',
  latin: 'TORANJ',
  accent: 'O',
  wordmark: 'TORANJ CAFE',
  assistant: 'دستیار ترنج',
  city: 'تهران',
  cityLatin: 'TEHRAN',
  address: 'تهران · خیابان نیلوفر · پلاک ۲۴',
  hours: 'هر روز ۸:۳۰ تا ۲۳:۳۰',
  handle: 'toranjcafe.demo',
  taglineLatin: 'GOOD COFFEE, GOOD COMPANY',
  taglineFa: 'قهوهٔ خوب، حال خوب',
}

// read straight from the env, so the brand never pulls the demo's café into the bundle
export const brand: Brand = import.meta.env.VITE_DEMO === '1' ? TORANJ : ONE_CAFE

/** The Latin name split around its orange letter: ["TOR", "O"…] for drawing the mark. */
export const wordmarkParts = (() => {
  const index = brand.latin.indexOf(brand.accent)
  if (index < 0) return [brand.latin, '', ''] as const
  return [brand.latin.slice(0, index), brand.accent, brand.latin.slice(index + 1)] as const
})()

/** "TORANJ CAFE · TEHRAN", the line a till prints at the foot of a receipt. */
export const receiptFooter = `${brand.wordmark} · ${brand.cityLatin}`
