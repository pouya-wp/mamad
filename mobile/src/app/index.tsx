import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import * as Notifications from 'expo-notifications';
import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Alert, BackHandler, Image, Linking, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import WebView, { type WebViewNavigation } from 'react-native-webview';

import { BUYER_SHORTCUTS, isPanelUrl, PANEL_ORIGIN, RESTAURANT_BUYER_SHORTCUTS, SHORTCUTS, WHO_SCRIPT } from '../lib/config';
import { registerPushScript, requestPushToken } from '../lib/push';

void SplashScreen.preventAutoHideAsync();

type Connection = 'loading' | 'online' | 'offline';

export default function HomeScreen() {
  const webRef = useRef<WebView>(null);
  const failedLoad = useRef(false);
  const [connection, setConnection] = useState<Connection>('loading');
  const [initialUrl, setInitialUrl] = useState(PANEL_ORIGIN + '/');
  const [currentUrl, setCurrentUrl] = useState(PANEL_ORIGIN + '/');
  const [canGoBack, setCanGoBack] = useState(false);
  const [webKey, setWebKey] = useState(0);
  const [pushBusy, setPushBusy] = useState(false);
  const [buyerScope, setBuyerScope] = useState<string | null>(null);
  // the panel decides what this account may open; the app only mirrors it in the tab bar
  const shortcuts = useMemo(
    () => (!buyerScope ? SHORTCUTS : buyerScope === 'Restaurant' ? RESTAURANT_BUYER_SHORTCUTS : BUYER_SHORTCUTS),
    [buyerScope],
  );
  const source = useMemo(() => ({ uri: initialUrl }), [initialUrl]);

  useEffect(() => {
    const subscription = BackHandler.addEventListener('hardwareBackPress', () => {
      if (canGoBack) {
        webRef.current?.goBack();
        return true;
      }
      return false;
    });
    return () => subscription.remove();
  }, [canGoBack]);

  const onLayout = useCallback(() => {
    void SplashScreen.hideAsync();
  }, []);

  const retry = useCallback(() => {
    setConnection('loading');
    setWebKey((key) => key + 1);
  }, []);

  const navigate = useCallback((path: string) => {
    void Haptics.selectionAsync();
    setConnection('loading');
    if (connection === 'offline') {
      setInitialUrl(PANEL_ORIGIN + path);
      setCurrentUrl(PANEL_ORIGIN + path);
      setWebKey((key) => key + 1);
    } else {
      webRef.current?.injectJavaScript(`window.location.assign(${JSON.stringify(PANEL_ORIGIN + path)}); true;`);
    }
  }, [connection]);

  useEffect(() => {
    function openNotificationPath(path: unknown) {
      if (path !== '/orders') return;
      setConnection('loading');
      setWebKey((key) => key + 1);
      setInitialUrl(PANEL_ORIGIN + path);
      setCurrentUrl(PANEL_ORIGIN + path);
    }
    const last = Notifications.getLastNotificationResponse();
    if (last) {
      openNotificationPath(last.notification.request.content.data?.path);
      void Notifications.clearLastNotificationResponse();
    }
    const subscription = Notifications.addNotificationResponseReceivedListener((response) => {
      openNotificationPath(response.notification.request.content.data?.path);
    });
    return () => subscription.remove();
  }, []);

  const registerPush = useCallback(async () => {
    if (pushBusy || connection !== 'online') return;
    setPushBusy(true);
    try {
      const token = await requestPushToken();
      webRef.current?.injectJavaScript(registerPushScript(token, Platform.OS));
    } catch (error) {
      Alert.alert('اعلان‌ها', error instanceof Error ? error.message : 'ثبت اعلان انجام نشد.');
      setPushBusy(false);
    }
  }, [connection, pushBusy]);

  const onMessage = useCallback((event: { nativeEvent: { data: string } }) => {
    try {
      const message = JSON.parse(event.nativeEvent.data);
      if (message.type === 'who') {
        setBuyerScope(typeof message.buyer === 'string' ? message.buyer : null);
        return;
      }
      if (message.type !== 'push') return;
      Alert.alert('اعلان‌ها', message.ok ? 'این گوشی برای اعلان‌ها ثبت شد.' : (message.message || 'ثبت اعلان انجام نشد.'));
    } catch {
      // Ignore messages unrelated to the native bridge.
    } finally {
      setPushBusy(false);
    }
  }, []);

  const onNavigation = useCallback((state: WebViewNavigation) => {
    if (!isPanelUrl(state.url)) return;
    setCurrentUrl(state.url);
    setCanGoBack(state.canGoBack);
  }, []);

  const allowNavigation = useCallback((request: { url: string }) => {
    if (isPanelUrl(request.url)) return true;
    if (request.url.startsWith('https://')) void Linking.openURL(request.url);
    return false;
  }, []);

  return (
    <SafeAreaView style={styles.root} edges={['top', 'bottom']} onLayout={onLayout}>
      <LinearGradient colors={['#20130f', '#0a0a0b']} style={styles.header}>
        <Pressable onPress={() => router.push('/about')} style={styles.brand} accessibilityLabel="دربارهٔ ONE CAFE">
          <Image source={require('../../assets/icon.png')} style={styles.logo} />
          <View>
            <Text style={styles.brandName}>ONE CAFE</Text>
            <Text style={styles.subtitle}>همراه مدیریت کافه</Text>
          </View>
        </Pressable>
        <View style={styles.actions}>
          <Pressable onPress={registerPush} disabled={pushBusy || connection !== 'online'} style={styles.iconButton} accessibilityLabel="فعال‌سازی اعلان‌ها">
            <Ionicons name="notifications-outline" size={21} color={connection === 'online' ? '#f5f2ec' : '#77716e'} />
          </Pressable>
          <Pressable onPress={() => webRef.current?.reload()} style={styles.iconButton} accessibilityLabel="تازه‌سازی پنل">
            <Ionicons name="refresh" size={21} color="#f5f2ec" />
          </Pressable>
        </View>
      </LinearGradient>

      <View style={styles.statusRow}>
        <View style={[styles.statusDot, connection === 'online' ? styles.online : connection === 'offline' ? styles.offline : styles.connecting]} />
        <Text style={styles.statusText}>{connection === 'online' ? 'متصل به پنل' : connection === 'offline' ? 'ارتباط برقرار نشد' : 'در حال اتصال…'}</Text>
        <Text style={styles.statusHint}>onecafe.beyondex.one</Text>
      </View>

      <View style={styles.content}>
        <WebView
          key={webKey}
          ref={webRef}
          source={source}
          originWhitelist={[PANEL_ORIGIN]}
          onShouldStartLoadWithRequest={allowNavigation}
          onNavigationStateChange={onNavigation}
          onMessage={onMessage}
          injectedJavaScript={WHO_SCRIPT}
          onLoadStart={() => { failedLoad.current = false; setConnection('loading'); }}
          onLoadEnd={(event) => { if (!failedLoad.current && event.nativeEvent.url !== 'about:blank') setConnection('online'); }}
          onError={() => { failedLoad.current = true; setConnection('offline'); }}
          onHttpError={(event) => { if (event.nativeEvent.statusCode >= 400) { failedLoad.current = true; setConnection('offline'); } }}
          javaScriptEnabled
          domStorageEnabled
          sharedCookiesEnabled
          thirdPartyCookiesEnabled={false}
          setSupportMultipleWindows={false}
          allowsBackForwardNavigationGestures
          style={styles.webview}
          containerStyle={styles.webContainer}
          startInLoadingState
          renderLoading={() => <View style={styles.loader}><ActivityIndicator size="large" color="#ff4f1a" /><Text style={styles.loaderText}>در حال باز کردن کافه…</Text></View>}
        />
        {connection === 'offline' && (
          <View style={styles.offlinePanel}>
            <Ionicons name="cloud-offline-outline" size={42} color="#ff6b42" />
            <Text style={styles.offlineTitle}>پنل در دسترس نیست</Text>
            <Text style={styles.offlineDetail}>اتصال اینترنت را بررسی کن و دوباره تلاش کن.</Text>
            <Pressable onPress={retry} style={styles.retryButton}><Text style={styles.retryText}>تلاش دوباره</Text></Pressable>
          </View>
        )}
      </View>

      <View style={styles.tabs}>
        {shortcuts.map((item) => {
          const active = new URL(currentUrl).pathname === item.path;
          return (
            <Pressable key={item.path} onPress={() => navigate(item.path)} style={[styles.tab, active && styles.activeTab]} accessibilityLabel={item.label}>
              <Ionicons name={item.icon} size={21} color={active ? '#ff6b42' : '#8d8580'} />
              <Text style={[styles.tabText, active && styles.activeTabText]}>{item.label}</Text>
            </Pressable>
          );
        })}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#0a0a0b' },
  header: { height: 70, paddingHorizontal: 16, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderBottomColor: '#34231c', borderBottomWidth: 1 },
  brand: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  logo: { width: 42, height: 42, borderRadius: 12 },
  brandName: { color: '#faf6f1', fontSize: 16, fontWeight: '800', letterSpacing: 1.5 },
  subtitle: { color: '#a79b93', fontSize: 10, marginTop: 2, textAlign: 'left' },
  actions: { flexDirection: 'row', gap: 6 },
  iconButton: { width: 38, height: 38, alignItems: 'center', justifyContent: 'center', borderRadius: 12, backgroundColor: '#241c19' },
  statusRow: { height: 27, backgroundColor: '#100f0f', flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, gap: 7 },
  statusDot: { width: 6, height: 6, borderRadius: 3 },
  online: { backgroundColor: '#64c78b' }, offline: { backgroundColor: '#ff5a3d' }, connecting: { backgroundColor: '#e5aa62' },
  statusText: { color: '#bbb2aa', fontSize: 10 }, statusHint: { color: '#69615b', fontSize: 10, marginLeft: 'auto' },
  content: { flex: 1 }, webview: { backgroundColor: '#0a0a0b' }, webContainer: { backgroundColor: '#0a0a0b' },
  loader: { flex: 1, backgroundColor: '#0a0a0b', alignItems: 'center', justifyContent: 'center', gap: 16 },
  loaderText: { color: '#bfb5ad', fontSize: 13 },
  offlinePanel: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0, backgroundColor: '#0a0a0b', justifyContent: 'center', alignItems: 'center', padding: 26 },
  offlineTitle: { color: '#faf6f1', fontSize: 20, fontWeight: '700', marginTop: 18 },
  offlineDetail: { color: '#a89d96', fontSize: 13, textAlign: 'center', marginTop: 10 },
  retryButton: { backgroundColor: '#ff4f1a', borderRadius: 14, paddingHorizontal: 28, paddingVertical: 13, marginTop: 26 },
  retryText: { color: '#fff', fontWeight: '700' },
  tabs: { height: 62, flexDirection: 'row', borderTopColor: '#33231d', borderTopWidth: 1, backgroundColor: '#12100f', paddingHorizontal: 8 },
  tab: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 3, borderTopWidth: 2, borderTopColor: 'transparent' },
  activeTab: { borderTopColor: '#ff4f1a' }, tabText: { color: '#8d8580', fontSize: 10 }, activeTabText: { color: '#ff6b42', fontWeight: '700' },
});
