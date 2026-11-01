export const PANEL_ORIGIN = 'https://onecafe.beyondex.one';

export const SHORTCUTS = [
  { path: '/', label: 'خانه', icon: 'grid-outline' },
  { path: '/orders', label: 'سفارش‌ها', icon: 'receipt-outline' },
  { path: '/menu', label: 'منو', icon: 'restaurant-outline' },
  { path: '/inventory', label: 'انبار', icon: 'cube-outline' },
] as const;

/** A purchase manager has their register; the restaurant's one also keeps the recipes. */
export const RESTAURANT_BUYER_SHORTCUTS = [
  { path: '/purchases', label: 'دفتر خرید', icon: 'cart-outline' },
  { path: '/menu', label: 'رسپی‌ها', icon: 'restaurant-outline' },
] as const;

export const BUYER_SHORTCUTS = [{ path: '/purchases', label: 'دفتر خرید', icon: 'cart-outline' }] as const;

/** Asks the panel, in its own session, who is signed in — the app only changes its tab bar. */
export const WHO_SCRIPT = `
  (async function () {
    try {
      const response = await fetch('/api/method/cafe_app.api.session.boot', { credentials: 'same-origin' });
      if (!response.ok) return;
      const user = ((await response.json()).message || {}).user || {};
      window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'who', buyer: user.buyer_scope || null }));
    } catch (error) {
      // signed out, or offline: the tab bar simply stays as it is
    }
  })();
  true;
`;

export function isPanelUrl(url: string) {
  if (url === 'about:blank') return true;
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'https:' && parsed.origin === PANEL_ORIGIN;
  } catch {
    return false;
  }
}
