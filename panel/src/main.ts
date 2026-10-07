import 'vazirmatn/Vazirmatn-font-face.css'
import './style.css'

import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import { brand } from './lib/brand'
import { DEMO, startDemoTraffic } from './demo'
import { installMotion } from './lib/motion'
import { installRipple } from './lib/ripple'
import { installSoundEvents } from './lib/sound'
import { router } from './router'

document.title = `${brand.name} · پنل مدیریت`

installMotion()
installRipple()
installSoundEvents()
if (DEMO) startDemoTraffic()
createApp(App).use(createPinia()).use(router).mount('#app')
