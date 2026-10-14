const CACHE='blackcore-mobile-shell-v1';
const SHELL=['./','./index.html','./manifest.webmanifest'];
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL))));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))));
self.addEventListener('fetch',e=>{if(new URL(e.request.url).pathname.includes('/api/'))return;e.respondWith(caches.match(e.request).then(c=>c||fetch(e.request)));});