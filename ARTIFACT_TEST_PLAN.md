# Artifact Loading Test Plan

## 🎯 Purpose
Verify that the Claude-style artifact loading experience works correctly:
- Loading animation shows during streaming (no raw HTML visible)
- Artifacts render smoothly when complete
- AI generates concise artifacts with real data
- Maps use traditional Leaflet rendering

---

## ✅ Pre-Test Checklist

### Verify Services Running
```bash
# Check backend
curl http://localhost:8000/health

# Check webapp
curl http://localhost:8501/health

# Or check processes
pgrep -f "uvicorn.*server.main:app"
pgrep -f "flask.*webapp/app.py"
```

### Open Browser
Navigate to: `http://localhost:8501/chat`

Open Developer Tools (F12) → Console tab to watch for errors

---

## 🧪 Test Cases

### Test 1: Simple Time-Series Chart
**Question:**
```
Show Brown Pelican population trends from 2010 to 2021
```

**Expected Behavior:**
1. ✅ Reasoning steps appear in collapsed section
2. ✅ AI answer streams in word by word
3. ✅ Loading animation appears: "📊 Creating visualization..."
4. ✅ **NO raw HTML visible** (no `<!DOCTYPE html>...`)
5. ✅ Loading animation pulses smoothly
6. ✅ When complete, line chart fades in showing years on X-axis, bird counts on Y-axis
7. ✅ Chart is interactive (hover shows values)
8. ✅ Download button appears in top-right
9. ✅ Data table appears below with all results
10. ✅ **NO map** (no geographic data)

**Success Criteria:**
- Chart shows ~7-11 data points (years 2010-2021)
- Y-axis uses actual bird count values from database
- Colors: #7BABAE (teal) for line
- Artifact is complete standalone HTML

---

### Test 2: Multi-Line Comparison Chart (Large Dataset)
**Question:**
```
Which colonies had decreasing bird counts over time?
```

**Expected Behavior:**
1. ✅ Reasoning steps show SQL generation and validation
2. ✅ AI answer explains declining colonies
3. ✅ Loading animation appears during artifact generation
4. ✅ **AI limits to top 10-20 colonies** (not all 236)
5. ✅ Multi-line chart fades in with 10 lines maximum
6. ✅ Legend shows colony names
7. ✅ Red/orange colors (#F04438, #FD853A) for declining trends
8. ✅ Data table shows **all results** (full 236 rows if applicable)
9. ✅ Map appears below showing all colony locations (traditional Leaflet)

**Success Criteria:**
- Artifact HTML is <10 KB (concise)
- Chart shows top 10 steepest declines only
- Map shows all colonies with Lat/Lon
- No Latitude/Longitude on chart axes

---

### Test 3: Bar Chart for Categories
**Question:**
```
Top 10 species by bird count in 2021
```

**Expected Behavior:**
1. ✅ Loading animation during generation
2. ✅ Bar chart fades in with 10 bars
3. ✅ X-axis: Species names
4. ✅ Y-axis: Bird counts
5. ✅ Bars sorted descending (highest first)
6. ✅ Coastal teal color (#7BABAE)
7. ✅ Data table with all species counts
8. ✅ **NO map** (no geographic data)

**Success Criteria:**
- Chart clean and readable
- Real species names from database
- Accurate count values

---

### Test 4: Geographic Query (Map Only, No Artifact)
**Question:**
```
Show all Louisiana colonies on a map
```

**Expected Behavior:**
1. ✅ AI answer describes Louisiana colonies
2. ✅ **NO artifact loading animation** (maps not in artifacts)
3. ✅ Data table appears first
4. ✅ Traditional Leaflet map appears below
5. ✅ Map markers show colony locations
6. ✅ Click markers for colony details popup
7. ✅ Fullscreen button works

**Success Criteria:**
- No artifact code block in AI response
- Map loads using traditional Leaflet rendering
- All LA colonies visible with markers

---

### Test 5: Simple Answer (No Visualization)
**Question:**
```
How many total bird observations were recorded in 2015?
```

**Expected Behavior:**
1. ✅ AI answer streams in
2. ✅ **NO loading animation** (simple answer, no chart needed)
3. ✅ Data table shows single row result
4. ✅ **NO chart** (not needed for single number)
5. ✅ **NO map** (no geographic data)

**Success Criteria:**
- Clean text answer only
- Data table confirms the number
- Fast response (<3 seconds)

---

## 🐛 Troubleshooting

### Issue: Raw HTML visible during streaming
**Symptom:** User sees `<!DOCTYPE html>...` in the chat
**Root Cause:** `hideArtifactsDuringStreaming()` not catching artifact blocks
**Fix:** Check regex pattern in line 389 of chat.js
```javascript
const artifactRegex = /```artifact\n([\s\S]*?)(?:```|$)/g;
```

### Issue: Loading animation never disappears
**Symptom:** Pulsing box stays forever
**Root Cause:** Artifact block not closed properly by AI
**Check:**
1. Look in browser console for parsing errors
2. Check if artifact has closing ` ``` `
3. Verify AI prompt includes closing instruction

### Issue: Chart doesn't render in iframe
**Symptom:** Blank white box instead of chart
**Root Cause:** JavaScript error in artifact HTML
**Debug:**
1. Right-click iframe → Inspect
2. Check iframe console for errors
3. Verify Chart.js loaded (https://cdn.jsdelivr.net/npm/chart.js@4.4.1)

### Issue: AI still plotting Lat/Lon on charts
**Symptom:** Chart X-axis shows latitude values
**Root Cause:** AI ignoring column selection rules
**Fix:** System prompt at line 1452-1455 of server/main.py emphasizes:
```
For Y-axis: Use count columns (Birds, Nests, total_birds, bird_count)
For X-axis: Use Year, Date, ColonyName, SpeciesName
NEVER use Latitude/Longitude for chart axes!
```

### Issue: Artifacts are too large (>50 KB)
**Symptom:** Slow loading, browser lag
**Root Cause:** AI including all data points instead of limiting
**Fix:** System prompt at line 1390-1394 instructs AI to limit to top 10-20 entries

---

## 📊 Performance Benchmarks

### Target Times:
- Simple chart (7 data points): 2-4 seconds total
- Complex chart (10 lines): 4-8 seconds total
- Map rendering: <1 second (after data table loads)

### Artifact Sizes:
- ✅ Good: 3-5 KB (10 data points)
- ⚠️ OK: 5-10 KB (20 data points)
- ❌ Bad: >10 KB (needs optimization)

---

## 🎬 Visual Flow

### What User Sees (Timeline):

```
[0s] User types question → clicks send
[0.5s] Reasoning section appears (collapsed)
[1s] "Analyzing question..."
[2s] "Generating SQL query..."
[3s] "Executing query..."
[3.5s] AI answer starts streaming: "Based on the data..."
[4s] Loading animation appears: 📊 Creating visualization...
       ┌─────────────────────────────┐
       │ 📊 Creating visualization... │
       │ ▓▓▓▓░░░░░░░░░░░░░░░░░░░░   │
       └─────────────────────────────┘
[5-7s] Text continues streaming (artifact code hidden)
[7.5s] Loading animation fades out
[8s] Chart fades in smoothly
[8.5s] Data table appears below
[9s] Map appears (if applicable)
[9s] Stream complete, input re-enabled
```

### What User NEVER Sees:
- ❌ Raw HTML: `<!DOCTYPE html><html><head>...`
- ❌ Incomplete artifact code
- ❌ JavaScript code streaming in
- ❌ Chart.js script tags

---

## 📝 Code Flow Reference

### Backend (server/main.py)
```python
# Line 2706: /ask/agentic/stream endpoint
# Line 1720: agentic_ask_stream() - main orchestrator
# Line 1917: generate_answer_stream() - includes artifacts
# Line 1386-1597: Artifact generation instructions in system prompt
```

### Frontend (webapp/static/js/chat.js)
```javascript
// Line 127: sendMessage() - initiates stream
// Line 192: handleStreamEvent() - processes each SSE event
// Line 296-301: hideArtifactsDuringStreaming() - replaces with loading animation
// Line 408-432: parseArtifacts() - extracts complete artifacts
// Line 434-475: renderArtifact() - creates iframe with artifact HTML
// Line 534-625: renderMap() - traditional Leaflet rendering (NOT artifacts)
```

---

## ✨ Success Indicators

### System is Working Correctly When:
1. ✅ No console errors in browser DevTools
2. ✅ Users never see raw HTML code
3. ✅ Loading animations smooth and professional
4. ✅ Charts render with real data from database
5. ✅ Large datasets limited to top 10-20 in charts
6. ✅ Full data still visible in data table
7. ✅ Maps use traditional Leaflet (not artifacts)
8. ✅ Download button exports working HTML
9. ✅ Artifacts are concise (<10 KB)
10. ✅ Response times under 10 seconds

---

## 🚀 Next Steps

After passing all tests:
1. ✅ Document any edge cases found
2. ✅ Update CLAUDE.md if architecture changes
3. ✅ Add screenshots to ARTIFACT_LOADING_FIX.md
4. ✅ Test with DevDays demo questions
5. ✅ Prepare for judge demonstration

---

**Last Updated:** 2026-03-14
**Status:** Ready for testing
**Expected Pass Rate:** 100% (all features implemented)
