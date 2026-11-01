import Constants from 'expo-constants';
import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

export async function requestPushToken(): Promise<string> {
  const projectId = Constants.expoConfig?.extra?.eas?.projectId ?? Constants.easConfig?.projectId;
  if (!projectId) {
    throw new Error('شناسهٔ پروژهٔ Expo هنوز تنظیم نشده است.');
  }

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('one-cafe-updates', {
      name: 'خبرهای ONE CAFE',
      importance: Notifications.AndroidImportance.DEFAULT,
      lightColor: '#ff4f1a',
    });
  }

  let permission = await Notifications.getPermissionsAsync();
  if (permission.status !== 'granted') permission = await Notifications.requestPermissionsAsync();
  if (permission.status !== 'granted') throw new Error('اجازهٔ اعلان در تنظیمات گوشی داده نشده است.');

  return (await Notifications.getExpoPushTokenAsync({ projectId })).data;
}

export function registerPushScript(token: string, platform: string) {
  // Runs in the panel's own HTTPS origin so the existing sid cookie and CSRF token are used.
  const payload = JSON.stringify({ token, platform });
  return `
    (async function () {
      try {
        const bootResponse = await fetch('/api/method/cafe_app.api.session.boot', { credentials: 'same-origin' });
        if (!bootResponse.ok) throw new Error('ابتدا در پنل وارد شوید.');
        const boot = (await bootResponse.json()).message;
        const response = await fetch('/api/method/cafe_app.api.mobile_push.register_device', {
          method: 'POST', credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': boot.csrf_token },
          body: JSON.stringify(${payload})
        });
        if (!response.ok) throw new Error('ثبت اعلان روی سرور ناموفق بود.');
        window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'push', ok: true }));
      } catch (error) {
        window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'push', ok: false, message: String(error.message || error) }));
      }
    })(); true;
  `;
}
