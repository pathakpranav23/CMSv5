## CODEP AURORA MARBLE — Theme Spec (v1)

This document is the single source of truth for the CodeP‑CloudEMS visual identity.

### Goal
Premium, calm, professional SaaS UI (control‑tower vibe). Never flat or boring. Mobile-first.

### Signature DNA (Non‑Negotiables)
1. Aurora background: layered radial gradients (cyan/teal + indigo/violet) with soft mist overlay.
2. Topbar coin controls: icon-only, perfectly circular “marble coin” buttons with tooltips.
3. Mobile topbar minimalism: on small screens show only Menu + Dashboard + Search/Command Palette.
4. Brand shine: “CodeP‑CloudEMS” in gradient‑shine text with subtle shadow.
5. Greeting chip: “Hello …” as a glass pill with a small glowing dot.
6. Glass surfaces: cards and nav feel translucent (blur) with soft borders/shadows.
7. Subtle motion: only micro hover lift/glow. No loud animations.

### Color System
**Atmosphere**
- Aurora Cyan: #22d3ee
- Aurora Indigo: #6366f1
- Aurora Mint: #34d399
- Mist overlays: rgba(255,255,255,0.06–0.20)
- Deep text: #0b1020

**Semantics**
- Success/Growth: cyan/mint family
- Warning: #f59e0b (sparingly)
- Danger: #fb7185 (sparingly)

### Background Recipe (Page Canvas)
Use multiple low-opacity radial gradients + mist. No single harsh banded gradient.
- Top-left: cyan glow (low opacity)
- Top-right: indigo glow (low opacity)
- Bottom: mint glow (very low opacity)
- White mist layer to keep the eye cool

### Topbar Rules
**Mobile**
- Visible actions: Menu + Dashboard + Search/Command Palette only
- Brand always visible
- Greeting moves to a second compact line under the bar; can hide on very tiny screens

**Desktop**
- Icon-first controls; tooltips for all icons
- Avoid text-heavy topbar; keep spacing premium

### Marble Coin Button Spec
- Must be a true 360° circle (strict width=height; cannot stretch)
- Icon-only; tooltip required
- Marble texture (marble_veins.svg) + glossy highlight
- Hover: lift 1px + stronger shadow
- Never appear as a capsule/pill

### Sidebar (Left Panel)
- Glassy panel with aurora tint and blur
- Grouped sections with subtle uppercase headers
- Hover: soft tint (glass hover)
- Active: slightly stronger tint + accent cue (line or glow dot)
- Mobile: off-canvas with backdrop

### Cards & Surfaces
- Rounded corners: 16–18px
- Translucent white surface, soft border, soft shadow
- Avoid heavy borders and flat solid blocks

### Footer Branding
- Dark premium gradient strip (navy → slate)
- CodeP logo + product name
- Workspace context line (small, subtle)
- Minimal, no clutter

### Do / Don’t
**Do**
- Keep palette cool, airy, professional
- Use glass + subtle glow
- Keep mobile topbar minimal

**Don’t**
- No pill/capsule buttons in topbar
- No loud neon colors or heavy animations
- No dense topbar text that breaks mobile

### Prompt Templates (copy/paste)
**Short**
Use CODEP AURORA MARBLE: aurora layered gradients, glass sidebar, glass cards, dark premium footer branding, topbar uses icon-only marble coin buttons (perfect circle) with tooltips; on mobile show only Menu+Dashboard+Search; brand title is gradient shine; greeting is a glass chip with glowing dot.

**Full**
Implement UI with a calm premium SaaS control-tower vibe. Use layered aurora radial gradients (cyan/indigo/mint) with mist overlay. Topbar uses strict circle marble coin icon buttons with tooltips; on small screens show only Menu+Dashboard+Search and move greeting to a second line. Sidebar is glass with grouped menus and subtle active/hover. Cards are translucent with soft borders/shadows and 16–18px radius. Footer is a dark premium gradient with CodeP branding and workspace context. Avoid pills/capsules in topbar and avoid loud neon.
