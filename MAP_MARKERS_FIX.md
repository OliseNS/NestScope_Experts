# Map Markers Not Showing - FIXED

## Problem
Map markers were not visible on the map. Users saw an empty map with no location pins.

## Root Cause
The issue was in how Plotly's `scatter_mapbox` handles marker sizing:

**What was wrong:**
```python
fig = px.scatter_mapbox(
    df_map,
    lat=lat_col,
    lon=lon_col,
    size_max=20  # ❌ No 'size' parameter provided!
)
```

Plotly's `scatter_mapbox` **requires** a `size` parameter (a column name or array) to display markers. Just setting `size_max` without `size` results in no markers being drawn.

Additionally, the `symbol='marker'` parameter doesn't work with mapbox - that's for regular scatter plots.

## Solution

**Fixed code:**
```python
# Add a constant size column
df_map['marker_size'] = 12  # All markers same size

fig = px.scatter_mapbox(
    df_map,
    lat=lat_col,
    lon=lon_col,
    size='marker_size',  # ✅ Now provides size data
    size_max=15,         # Controls maximum display size
    mapbox_style="open-street-map",
    color_discrete_sequence=['#D97757']
)

fig.update_traces(
    marker=dict(
        opacity=0.9,
        sizemode='diameter'  # Consistent sizing
    )
)
```

**Key changes:**
1. ✅ Added `marker_size` column with value 12 (constant for all points)
2. ✅ Used `size='marker_size'` parameter in scatter_mapbox
3. ✅ Set `size_max=15` to control final display size
4. ✅ Removed invalid `symbol='marker'` (doesn't work with mapbox)
5. ✅ Simplified marker configuration to just opacity and sizemode

## How to Test

1. **Open NestChat**: http://localhost:8501 → NestChat
2. **Ask**: "Show me all colonies in Louisiana with their locations"
3. **Check map tab**: You should now see **visible orange circular markers**
4. **Hover over markers**: Should show colony name and coordinates

### Expected Result

**Before (broken):**
- Empty map, no markers visible
- Just the base map tiles

**After (fixed):**
- **Orange circular markers** (~15px diameter)
- Visible at all zoom levels
- Hover shows colony information

## Technical Details

### Plotly scatter_mapbox Requirements

For markers to appear in `px.scatter_mapbox`, you MUST provide:
1. **lat** and **lon** columns (latitude/longitude data)
2. **size** parameter pointing to a column or array of numeric values

Optional but recommended:
- `size_max`: Maximum marker size in pixels (default: 20)
- `color`: Color column or discrete sequence
- `hover_name` and `hover_data`: Hover information

### Why Constant Size?

We use a constant size (`marker_size = 12`) because:
- All colony locations should have equal visual weight
- Varying marker sizes would require a meaningful metric (e.g., bird count)
- Consistent sizing is clearer for geographic visualization
- Risk analysis page uses varying sizes based on risk score (appropriate there)

### Alternative: Variable Marker Sizes

If you want markers sized by bird population:

```python
# Use bird count for marker size
fig = px.scatter_mapbox(
    df_map,
    lat=lat_col,
    lon=lon_col,
    size='total_birds',  # Markers scale with population
    size_max=20,
    hover_name='ColonyName'
)
```

This works well for the **Flood Intelligence** page where marker size represents risk score.

## Files Modified

- `frontend/components/maps.py` (lines 138-165)

## Status

✅ **FIXED** - Markers now show correctly
✅ **Streamlit restarted** - Changes are live
✅ **No errors** in logs

## Test It Now

Open http://localhost:8501 and navigate to NestChat. Ask any location-based question and you should see markers on the map!

---

**Note**: The risk zones map on the Flood Intelligence page was not affected by this bug - it already had proper `size` parameter using risk scores.
