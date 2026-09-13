---
name: svg-subject-illustrations
description: "Use when adding animated SVG to subject UI cards."
version: 1.0.0
author: "Hermes Agent"
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [svg, animation, illustration, education, react, tailwind]
    related_skills: [frontend-ui-engineering, frontend-design, donghanh]
---

# SVG Subject Illustrations — Animated, Pure SMIL

Dùng khi cần tạo hình minh họa động cho trang môn học / domain-based UI. Kỹ thuật: **SVG SMIL thuần tuý** — không Framer Motion, GSAP, hay Lottie.

## Nguyên tắc

- Palette khớp domain (emerald→Tiếng Anh, blue/cyan→Toán, purple→Vật lý, amber→Hóa, rose→Sinh, indigo→Lp trình)
- `aria-hidden="true"` trên mọi illustration — chỉ trang trí, không interactive
- `viewBox="0 0 200 160"` là tỷ lệ chuẩn
- `<defs>` với id prefix riêng mỗi illustration để tránh conflict khi nhiều cái cùng trang

## Component API

```tsx
<SubjectIllustration subjectId="mathematics" size="md" className="..." />
// size: 'sm'|'md'|'lg'|'hero' — sm=80px, md=90px, lg=140px, hero=165px (h)
```

## SMIL patterns thường dùng

### Di chuyển dọc path
```svg
<circle r="5"><animateMotion path="M 8,80 C..." dur="4s" repeatCount="indefinite" /></circle>
```

### Quỹ đạo với mpath
```svg
<circle r="5">
  <animateMotion dur="3s" repeatCount="indefinite"><mpath href="#orbit-id" /></animateMotion>
</circle>
<!-- style="display:none" không dùng visibility:hidden — trình duyệt cần phần tử có trong layout -->
<ellipse id="orbit-id" ... fill="none" style="display:none" />
```

### Dao động quay
```svg
<animateTransform attributeName="transform" type="rotate"
  values="-5 100 80; 5 100 80; -5 100 80"
  dur="1.6s" repeatCount="indefinite"
  calcMode="spline" keySplines="0.4 0 0.6 1; 0.4 0 0.6 1" keyTimes="0; 0.5; 1" />
```

### Vẽ đường cong từ từ
```svg
<path strokeDasharray="420" strokeDashoffset="420">
  <animate attributeName="stroke-dashoffset" from="420" to="0" dur="2.2s" fill="freeze" />
</path>
```

### Trượt group (DNA scroll)
```svg
<g><animateTransform attributeName="transform" type="translate"
  from="0,0" to="0,-20" dur="3s" repeatCount="indefinite"
  calcMode="spline" keySplines="0.4 0 0.6 1" keyTimes="0;1" /></g>
```

## Dùng trong card list (nền mờ)

```tsx
<div className="absolute top-0 right-0 opacity-[0.08] pointer-events-none select-none" aria-hidden="true">
  <SubjectIllustration subjectId={sub.id} size="hero" />
</div>
```

`pointer-events-none select-none` bắt buộc — nếu thiếu sẽ chặn click/tap.

## Hero banner (SubjectDetail)

```tsx
const subjectTheme: Record<string, { from: string; via: string; to: string; accent: string; ring: string }> = {
  mathematics: { from: 'from-blue-600/30', via: 'via-cyan-600/15', to: 'to-indigo-600/20', accent: 'text-blue-400', ring: 'ring-blue-500/30' },
  physics:     { from: 'from-purple-600/30', via: 'via-violet-600/15', to: 'to-indigo-600/20', accent: 'text-purple-400', ring: 'ring-purple-500/30' },
  chemistry:   { from: 'from-amber-600/30', via: 'via-orange-600/15', to: 'to-yellow-600/20', accent: 'text-amber-400', ring: 'ring-amber-500/30' },
  biology:     { from: 'from-rose-600/30', via: 'via-pink-600/15', to: 'to-red-600/20', accent: 'text-rose-400', ring: 'ring-rose-500/30' },
  english:     { from: 'from-emerald-600/30', via: 'via-teal-600/15', to: 'to-green-600/20', accent: 'text-emerald-400', ring: 'ring-emerald-500/30' },
  programming: { from: 'from-indigo-600/30', via: 'via-blue-600/15', to: 'to-violet-600/20', accent: 'text-indigo-400', ring: 'ring-indigo-500/30' },
}
// Non-null assertion bắt buộc (TypeScript strict mode):
// const theme = (subjectTheme[subjectId ?? ''] ?? subjectTheme['mathematics'])!
```

Animation nổi lên xuống: `<div className="animate-float">` (xem Tailwind keyframes bên dưới).

## Tailwind keyframes cần thêm

```js
keyframes: {
  float: { '0%, 100%': { transform: 'translateY(0px)' }, '50%': { transform: 'translateY(-8px)' } },
  orbit: { '0%': { transform: 'rotate(0deg) translateX(48px) rotate(0deg)' }, '100%': { transform: 'rotate(360deg) translateX(48px) rotate(-360deg)' } },
  'glow-pulse': { '0%, 100%': { boxShadow: '0 0 20px 4px rgba(var(--a-500)/0.25)' }, '50%': { boxShadow: '0 0 36px 8px rgba(var(--a-500)/0.45)' } },
},
animation: {
  float: 'float 4s ease-in-out infinite',
  orbit: 'orbit 8s linear infinite',
  'glow-pulse': 'glow-pulse 3s ease-in-out infinite',
},
```

Stagger: `style={{ animationDelay: \`${idx * 60}ms\` }}` trên card cha để cascade.

## Pitfalls

- **SVG id conflict**: Prefix riêng mỗi illustration (vd `const id = 'math-ill'`) khi nhiều cái cùng trang.
- **TypeScript strict Record**: `subjectTheme[key]` có type `| undefined` — dùng `(... ?? fallback)!`.
- **`display:none` để ẩn mpath source**: `visibility:hidden` không đủ.
- **Tailwind dynamic class**: `${theme.from}` phải là chuỗi đầy đủ để JIT giữ lại class.
