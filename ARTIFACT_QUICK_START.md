# Artifact System - Quick Start Guide

## 🎯 What Are Artifacts?

Artifacts are **interactive visualizations** that the AI generates directly in chat responses. Think of them as mini-dashboards, charts, and data displays that are:
- ✅ **Theme-aware** (match light/dark mode)
- ✅ **Interactive** (hover for details, responsive)
- ✅ **Professional** (beautiful design, modern UI)
- ✅ **Multi-artifact** (combine multiple visualizations)

---

## 🚀 Try These Example Prompts

### 1. Population Dashboard (Best Demo)
```
Create a comprehensive dashboard showing:
1) Total bird and nest counts 2010-2021
2) Top 5 species breakdown in 2021
3) Year-over-year growth rates
```
**You'll get:** Metric cards + trend chart + species bar chart

### 2. Species Comparison
```
Compare Brown Pelican, Laughing Gull, and Royal Tern population trends from 2010 to 2021. Show a multi-line chart.
```
**You'll get:** Color-coded multi-line chart comparing 3 species

### 3. Colony Hotspots
```
Show top 10 colonies by total bird count with their locations on a map
```
**You'll get:** Bar chart ranking + auto-generated interactive map

### 4. Decline Analysis
```
Analyze colonies with declining populations. Show the decline trends and metrics.
```
**You'll get:** Impact metric cards + multi-line decline trends

---

## 🎨 What Makes Artifacts Special?

### Theme Integration
- Artifacts **automatically match** your UI theme
- Toggle light/dark mode → artifacts update instantly
- No blinding white backgrounds in dark mode!

### Dashboard Style
- Multiple coordinated visualizations in one response
- Metric cards + charts + maps working together
- Professional design with subtle animations

### Beautiful UI
- **Large, Readable Text**: 32px values, 18px titles
- **Clean Cards**: Rounded corners, subtle shadows
- **Hover Effects**: Interactive feedback
- **Color Palette**: Coastal theme (teal, ocean blue, sea foam)

---

## 📐 Artifact Types

### 1. Metric Cards
**Use for:** Summary statistics, KPIs
```
Show total birds, nests, colonies, and species for 2021
```
**Result:** 4 beautiful metric cards with icons and growth indicators

### 2. Line Charts
**Use for:** Trends over time
```
Show Brown Pelican population trends 2010-2021
```
**Result:** Smooth line chart with fill, points, and hover tooltips

### 3. Bar Charts
**Use for:** Rankings, comparisons
```
What were the top 5 species by bird count in 2021?
```
**Result:** Color-coded horizontal bar chart

### 4. Multi-Line Charts
**Use for:** Comparing multiple entities
```
Compare Louisiana, Texas, and Mississippi bird populations over time
```
**Result:** Multi-line chart with 3 color-coded lines

### 5. Dashboards
**Use for:** Comprehensive overviews
```
Create a dashboard for [any topic]
```
**Result:** 2-4 coordinated artifacts (cards + charts)

---

## 💡 Pro Tips

### Get Multiple Artifacts
Use keywords:
- "Create a dashboard..."
- "Show metrics and trends..."
- "Comprehensive analysis..."
- "Include charts and data..."

### Be Specific
```
❌ "Show bird data"
✅ "Show 2010-2021 bird counts with trend chart and top 5 species"
```

### Request Comparisons
```
"Compare [A] vs [B] across [timeframe]"
```

### Combine Visualizations
```
"Show [metric] with a chart and map"
```

---

## 🎨 Color Scheme

### Coastal Theme Colors
- **Coastal Teal**: #7BABAE (primary charts)
- **Ocean Blue**: #537C8A (accents)
- **Sea Foam**: Light teal variations
- **Driftwood**: Secondary text
- **Beach Sand**: Light backgrounds

### Status Colors
- **Success/Growth**: #4a9d5f (green)
- **Warning**: #d4a02f (amber)
- **Danger/Decline**: #c74a4a (red)
- **Info**: #4a7f9d (blue)

---

## 🔧 Behind the Scenes

### How Theme-Awareness Works
1. System detects current theme (light/dark)
2. Injects CSS variables into artifact HTML
3. Artifact uses variables for all colors
4. Theme toggle updates all artifacts in real-time

### CSS Variables Available
```css
--theme-bg-primary        /* Main background */
--theme-surface           /* Card background */
--theme-text-primary      /* Main text */
--theme-text-secondary    /* Secondary text */
--theme-coastal           /* Coastal teal */
--theme-ocean             /* Ocean blue */
--theme-border            /* Borders */
```

---

## ⚡ Quick Reference

### Dashboard Keywords
- "dashboard"
- "comprehensive"
- "overview"
- "metrics and trends"

### Chart Keywords
- "chart", "graph", "plot"
- "show trends"
- "compare"
- "top N", "ranking"

### Comparison Keywords
- "compare [A] vs [B]"
- "multi-line"
- "side by side"
- "across [dimension]"

### Geographic Keywords
- "with map"
- "show locations"
- "geographic distribution"
- "colonies in [state]"

---

## 🎯 Real-World Examples

### For Research Papers
```
Create a comprehensive analysis of Brown Pelican recovery 2010-2021 with population trends, growth metrics, and geographic distribution
```

### For Stakeholder Meetings
```
Show me a dashboard: Louisiana bird populations, top colonies, and year-over-year changes
```

### For Grant Proposals
```
Analyze biodiversity across restoration sites. Include species counts, population trends, and colony locations.
```

### For Emergency Response
```
Which colonies need immediate attention? Show declining populations with severity metrics and locations.
```

---

## ✨ Feature Highlights

### ✅ What Works
- Theme-aware colors (light/dark)
- Multi-artifact dashboards
- Interactive hover tooltips
- Real-time theme updates
- Responsive layouts
- Beautiful metric cards
- Professional charts

### 🗺️ Auto-Generated
- Maps (when query includes Lat/Lon)
- Data tables (always shown)

### 📊 Artifact Types
- Metric cards (KPIs)
- Line charts (trends)
- Bar charts (rankings)
- Multi-line charts (comparisons)
- Full dashboards (combined)

---

## 🚀 Start Exploring!

**Click on any example prompt in NestChat to see artifacts in action!**

The new artifact system transforms raw data into beautiful, interactive visualizations that tell compelling stories about Gulf Coast bird populations.

**Pro Tip:** Toggle between light and dark mode to see the theme integration in action!

---

Made with 💙 by The Water Institute + Claude
