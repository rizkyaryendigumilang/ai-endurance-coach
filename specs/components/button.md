---
name: Button
tier: component
status: stable
last-updated: 2026-10-27
source: foundations/color.md, foundations/spacing.md, foundations/typography.md, foundations/borders.md, foundations/shadows.md, specs/Tokens/aliases.md
---

# Button

> Buttons are the primary mechanism for user action. Every button must be immediately recognizable as clickable, sized for touch, and clearly communicate its intent and priority. Sized with athletic round pill styling (`Radius/Pill` = 9999px) and Strava-inspired high-visibility athletic colors. Only one high-emphasis button should appear per section.

---

## Variants

Five variants cover every action type in the product.

| Variant | Description | Example |
|---------|-------------|---------|
| `primary` | Strava-orange fill (#FC4C02). The single most important action in a view. | "Start Session", "Record Workout" |
| `action` | Strava-orange fill (#FC4C02). High-urgency athletic CTAs — used for primary triggers or live recording. | "Start Activity", "Sync Telemetry" |
| `outline` | White background with Strava-orange border. Secondary action alongside a primary. | "Sign In", "Customize in AI Chat" |
| `ghost` | Subtle orange fill (#FFF3ED), orange label. Tertiary actions that expand or reveal content. | "View Analysis", "3 more options" |
| `link` | Text only, no background or border. Inline contextual actions embedded in content. | "View Training Log" |

> **One `action` or `primary` per section.** Never place two high-emphasis buttons side by side. Pair `primary` + `outline` or `action` + `outline`.

---

## Sizes

| Size | Min height | Padding (V × H) | Typography | Radius | Icon size |
|------|-----------|-----------------|------------|--------|-----------|
| `lg` | 52px | `Spacing/LG` × `Spacing/2XL` | `Typography/Body/LG` | `Radius/Pill` (9999px) | `Icon/Size/Default` (24px) |
| `md` | 44px | `Spacing/MD` × `Spacing/XL` | `Typography/Label/MD` | `Radius/Pill` (9999px) | `Icon/Size/Default` (24px) |
| `sm` | 32px | `Spacing/SM` × `Spacing/MD` | `Typography/Label/SM` | `Radius/Pill` (9999px) | `Icon/Size/Compact` (20px) |

> **Touch target:** `sm` buttons are visually 32px but must have a 44×44px invisible hit area via padding or wrapper. Never reduce the hit area below 44px.

---

## Icon Placement

| Slot | Position | Gap | Usage |
|------|----------|-----|-------|
| `leading` | Icon left of label | `Spacing/XS` | Activity icon, action icons — "Record", "Sync" |
| `trailing` | Icon right of label | `Spacing/XS` | Expand/collapse — "More options ∨" |
| `icon-only` | No label | — | Compact toolbars only. Always include an accessible label. |

Icon size follows the size scale: `md` and `lg` use `Icon/Size/Default` (24px); `sm` uses `Icon/Size/Compact` (20px).

---

## Token Map — Primary

Strava orange fill. The brand CTA ("Start Session", "Log Workout").

| Property | State | Token | Resolved value |
|----------|-------|-------|----------------|
| Background | Default | `Color/Fill/Brand/Default` | `Primary/500` (#FC4C02) |
| Background | Hover | `Color/Fill/Brand/Hover` | `Primary/600` (#E34402) |
| Background | Active | `Color/Fill/Active` | `Primary/700` (#C93B00) |
| Background | Disabled | `Color/Fill/Disabled` | `Neutral/200` (#E0E0E0) |
| Label | Default | `Color/Text/On-Color` | `Neutral/50` (#FFFFFF) |
| Label | Disabled | `Color/Text/Disabled` | `Neutral/300` (#BDBDBD) |
| Border | All | none | — |
| Focus ring | Focus | `Color/Focus/Default` | `Primary/500` (#FC4C02) |
| Shadow | Default | `Elevation/Resting` | none |
| Shadow | Hover | `Elevation/Subtle` | `shadow-xs` |
| Border radius | All | `Radius/Pill` | 9999px |

---

## Token Map — Action

Strava orange fill. High-urgency CTA ("Record", "Sync").

| Property | State | Token | Resolved value |
|----------|-------|-------|----------------|
| Background | Default | `Color/Fill/Action/Default` | `Action/500` (#FC4C02) |
| Background | Hover | `Color/Fill/Action/Hover` | `Action/600` (#E34402) |
| Background | Active | `Color/Fill/Active` | `Action/700` (#C93B00) |
| Background | Disabled | `Color/Fill/Disabled` | `Neutral/200` (#E0E0E0) |
| Label | Default | `Color/Text/On-Color` | `Neutral/50` (#FFFFFF) |
| Label | Disabled | `Color/Text/Disabled` | `Neutral/300` (#BDBDBD) |
| Border | All | none | — |
| Focus ring | Focus | `Color/Focus/Default` | `Action/500` (#FC4C02) |
| Shadow | Default | `Elevation/Resting` | none |
| Shadow | Hover | `Elevation/Subtle` | `shadow-xs` |
| Border radius | All | `Radius/Pill` | 9999px |

---

## Token Map — Outline

White background, Strava-orange border ("Sign In", "Customize in AI Chat").

| Property | State | Token | Resolved value |
|----------|-------|-------|----------------|
| Background | Default | `Color/Surface/Default` | `Neutral/50` (#FFFFFF) |
| Background | Hover | `Color/Surface/Hover` | `Primary/50` (#FFF3ED) |
| Background | Active | `Color/Surface/Active` | `Primary/100` (#FFE5D6) |
| Background | Selected | `Color/Fill/Brand/Default` | `Primary/500` (#FC4C02) |
| Background | Disabled | `Color/Fill/Disabled` | `Neutral/200` (#E0E0E0) |
| Label | Default | `Color/Text/Brand` | `Primary/500` (#FC4C02) |
| Label | Hover | `Color/Text/Brand-Hover` | `Primary/600` (#E34402) |
| Label | Selected | `Color/Text/On-Color` | `Neutral/50` (#FFFFFF) |
| Label | Disabled | `Color/Text/Disabled` | `Neutral/300` (#BDBDBD) |
| Border | Default | `Color/Border/Brand` | `Primary/500` (#FC4C02) |
| Border | Hover | `Color/Border/Hover` | `Primary/600` (#E34402) |
| Border | Selected | `Color/Fill/Brand/Default` | `Primary/500` (#FC4C02) |
| Border | Disabled | `Color/Border/Disabled` | `Neutral/200` (#E0E0E0) |
| Border width | All | 1.5px | — |
| Focus ring | Focus | `Color/Focus/Default` | `Primary/500` (#FC4C02) |
| Border radius | All | `Radius/Pill` | 9999px |

---

## Token Map — Ghost

Subtle orange fill (#FFF3ED), orange label ("View Analysis", "3 more options").

| Property | State | Token | Resolved value |
|----------|-------|-------|----------------|
| Background | Default | `Color/Fill/Brand/Subtle` | `Primary/50` (#FFF3ED) |
| Background | Hover | `Color/Fill/Brand/Subtle-Hover` | `Primary/100` (#FFE5D6) |
| Background | Active | `Color/Fill/Brand/Subtle-Hover` | `Primary/100` (#FFE5D6) |
| Background | Disabled | `Color/Fill/Disabled` | `Neutral/200` (#E0E0E0) |
| Label | Default | `Color/Text/Brand` | `Primary/500` (#FC4C02) |
| Label | Hover | `Color/Text/Brand-Hover` | `Primary/600` (#E34402) |
| Label | Disabled | `Color/Text/Disabled` | `Neutral/300` (#BDBDBD) |
| Border | All | none | — |
| Focus ring | Focus | `Color/Focus/Default` | `Primary/500` (#FC4C02) |
| Border radius | All | `Radius/Pill` | 9999px |

---

## Token Map — Link

Text only. No background, no border, no padding ("View Training Log").

| Property | State | Token | Resolved value |
|----------|-------|-------|----------------|
| Background | All | none | — |
| Label | Default | `Color/Text/Brand` | `Primary/500` (#FC4C02) |
| Label | Hover | `Color/Text/Brand-Hover` | `Primary/600` (#E34402) |
| Label | Disabled | `Color/Text/Disabled` | `Neutral/300` (#BDBDBD) |
| Border | All | none | — |
| Padding | All | 0 | 0 |
