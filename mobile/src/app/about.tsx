import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function AboutScreen() {
  return (
    <SafeAreaView style={styles.root} edges={['top', 'bottom']}>
      <LinearGradient colors={['#2c1710', '#0a0a0b']} style={styles.hero}>
        <Pressable onPress={() => router.back()} style={styles.back} accessibilityLabel="بازگشت">
          <Ionicons name="arrow-forward" size={24} color="#f9f4ed" />
        </Pressable>
        <Image source={require('../../assets/icon.png')} style={styles.logo} />
        <Text style={styles.title}>ONE CAFE</Text>
        <Text style={styles.subtitle}>همراه مدیریت کافه</Text>
      </LinearGradient>
      <View style={styles.card}>
        <Text style={styles.heading}>همیشه نزدیک به کافه</Text>
        <Text style={styles.text}>سفارش‌ها، منو و انبار از پنل آنلاین ONE CAFE نمایش داده می‌شوند. برای دیدن داده‌های تازه، گوشی باید به اینترنت وصل باشد.</Text>
      </View>
      <View style={styles.card}>
        <Text style={styles.heading}>اعلان‌ها</Text>
        <Text style={styles.text}>پس از راه‌اندازی سرویس اعلان و ورود به پنل، دکمهٔ زنگ بالای صفحه این گوشی را ثبت می‌کند. اجازهٔ سیستم عامل فقط همان موقع درخواست می‌شود.</Text>
      </View>
      <Text style={styles.version}>نسخهٔ ۰٫۱٫۰</Text>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#0a0a0b' },
  hero: { height: 300, alignItems: 'center', justifyContent: 'center' },
  back: { position: 'absolute', right: 18, top: 18, width: 42, height: 42, borderRadius: 14, backgroundColor: '#39241c', alignItems: 'center', justifyContent: 'center' },
  logo: { width: 86, height: 86, borderRadius: 22, marginBottom: 18 },
  title: { color: '#faf6f1', fontSize: 31, fontWeight: '800', letterSpacing: 2 },
  subtitle: { color: '#c3b5ab', fontSize: 14, marginTop: 8 },
  card: { marginHorizontal: 18, marginTop: 16, backgroundColor: '#171311', borderColor: '#382720', borderWidth: 1, borderRadius: 20, padding: 20 },
  heading: { color: '#ff794b', fontSize: 16, fontWeight: '700', textAlign: 'right' },
  text: { color: '#c5bcb4', fontSize: 13, lineHeight: 26, marginTop: 9, textAlign: 'right' },
  version: { color: '#756b64', fontSize: 11, textAlign: 'center', marginTop: 'auto', marginBottom: 14 },
});
