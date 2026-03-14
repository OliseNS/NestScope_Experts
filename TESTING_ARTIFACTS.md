# Testing NestChat Artifacts - Quick Guide

## 🚀 Quick Start

1. **Restart Services**
```bash
# Kill existing processes
pkill -f uvicorn
pkill -f "python webapp/app.py"
pkill -f "python labeller/app.py"

# Restart all
./run_webapp.sh
```

2. **Open NestChat**
```
http://localhost:8501/chat
```

---

## 🧪 Test Cases

### Test 1: Time-Series Trend (Line Chart)
**Question:**
```
Show me Brown Pelican population trends from 2010 to 2021
```

**Expected Result:**
- ✅ Text answer with statistics
- ✅ Artifact with line chart showing years on X-axis, bird counts on Y-axis
- ✅ Data table with results
- ✅ Reasoning section showing SQL validation

**Check:**
- Look for ````artifact` in the answer
- Chart should show actual years (2010, 2015, 2021) and counts
- Should NOT plot Latitude/Longitude!

---

### Test 2: Declining Populations (Multi-Line Chart)
**Question:**
```
Which colonies had decreasing bird counts over time?
```

**Expected Result:**
- ✅ Text answer identifying declining colonies
- ✅ Artifact with multi-line chart showing multiple colonies
- ✅ Map artifact showing geographic distribution
- ✅ Data table with full results

**Check:**
- Should have 2 artifacts (chart + map)
- Chart Y-axis should be bird counts (not coordinates!)
- Map should show markers for colonies

---

### Test 3: Geographic Query (Map)
**Question:**
```
Show all bird colonies in Louisiana with their coordinates
```

**Expected Result:**
- ✅ Text answer listing colonies
- ✅ Artifact with interactive Leaflet map
- ✅ Data table with colony names, lat/lon
- ✅ No chart (not time-series data)

**Check:**
- Map should have markers for each colony
- Click markers to see popup with details
- Should NOT generate a chart

---

### Test 4: Category Comparison (Bar Chart)
**Question:**
```
What were the top 5 species by bird count in 2021?
```

**Expected Result:**
- ✅ Text answer with rankings
- ✅ Artifact with bar chart showing species comparison
- ✅ Data table with results

**Check:**
- Bar chart with species names on X-axis
- Bird counts on Y-axis
- Should use coastal theme colors (#7BABAE)

---

## 🔍 What to Look For

### ✅ Good Artifact:
```artifact
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1"></script>
    <style>
        body { margin: 20px; font-family: sans-serif; }
        h3 { color: #7BABAE; }
    </style>
</head>
<body>
    <h3>Brown Pelican Trends</h3>
    <canvas id="myChart"></canvas>
    <script>
        new Chart(document.getElementById('myChart'), {
            type: 'line',
            data: {
                labels: [2010, 2015, 2021],
                datasets: [{
                    label: 'Bird Count',
                    data: [45328, 69123, 112043],
                    borderColor: '#7BABAE'
                }]
            }
        });
    </script>
</body>
</html>
```

### Artifact Rendering:
1. Artifact appears below the text answer
2. Rendered in an iframe (isolated from page)
3. Has a "Download HTML" button in top-right
4. Chart/map is fully interactive

### Reasoning Section:
1. Click "Show reasoning" to expand
2. Should show:
   - SQL query used
   - Validation steps
   - Any retry attempts

---

## 🐛 Common Issues

### Issue: No artifacts showing
**Debug:**
1. Check browser console for errors
2. Look for ```artifact in the AI response
3. Verify iframe is being created: `document.querySelectorAll('.artifact-iframe')`

**Fix:**
- Make sure backend is using the updated `generate_answer_stream()`
- Check if parseArtifacts() is being called

---

### Issue: Artifacts show but charts don't render
**Debug:**
1. Right-click iframe → Inspect
2. Check console inside iframe
3. Verify Chart.js is loaded

**Common causes:**
- CDN blocked (check network tab)
- JavaScript error in artifact HTML
- Missing canvas element

---

### Issue: Maps don't show
**Debug:**
1. Check if results have Latitude/Longitude columns
2. Verify Leaflet CSS is loaded
3. Check iframe console for errors

**Common causes:**
- No Lat/Lon in query results
- AI didn't generate map artifact
- Leaflet CDN blocked

---

## 📊 Expected Output Example

For "Which colonies had decreasing bird counts?":

```
**Text Answer:**
I analyzed bird population trends and found 236 colonies with declining populations...

[Detailed analysis with numbers]

**Artifact 1: Line Chart**
[Interactive chart showing Breton Island, Felicity Island trends]

**Artifact 2: Map**
[Interactive map with markers for declining colonies]

**Data Table:**
[Full results with colony names, years, bird counts]

**Reasoning Section (expandable):**
- SQL Query: SELECT...
- Validation: Query structure looks good...
- Execution: Returned 236 rows
```

---

## ✅ Success Checklist

- [ ] Artifacts render in iframes below answers
- [ ] Charts use correct columns (counts, not coordinates)
- [ ] Maps show for geographic queries
- [ ] Download buttons work
- [ ] Reasoning section is expandable
- [ ] Data table always shows
- [ ] Multiple artifacts can appear in one answer

---

## 🔧 Quick Fixes

### Restart Backend Only:
```bash
pkill -f uvicorn
python -m uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
```

### Check Logs:
```bash
tail -f logs/webapp.log
tail -f logs/server.log
```

### Test Artifact Parsing:
```javascript
// In browser console
const text = "Here's the answer\n\n```artifact\n<html>test</html>\n```\n\nMore text";
const { cleanAnswer, artifacts } = nestChat.parseArtifacts(text);
console.log('Artifacts found:', artifacts.length);
```

---

## 📝 Notes

1. **Artifacts vs Old System:**
   - OLD: Backend sent `[SHOW_CHART: line]` → Frontend generated Chart.js
   - NEW: Backend generates complete HTML → Frontend renders in iframe

2. **Why Iframes:**
   - Isolation (artifact CSS doesn't affect page)
   - Security (sandboxed execution)
   - Portability (easy to download)

3. **AI Decision Making:**
   - AI sees query results table
   - Extracts actual data values
   - Chooses appropriate visualization type
   - Generates complete HTML with real data

4. **Column Selection:**
   - AI understands which columns are counts vs coordinates
   - Never plots Latitude/Longitude on trend charts
   - Uses Lat/Lon ONLY for maps

---

Made with 🐦 for DevDays 2026
