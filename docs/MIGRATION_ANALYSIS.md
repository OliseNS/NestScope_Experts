# Migration Analysis Guide

Understanding bird migration patterns using breeding colony data.

---

## Important Limitations

This dataset tracks **breeding colonies only** - not full migration routes.

**What You CAN Analyze:**
- ✅ Species presence/absence at colonies over time
- ✅ Seasonal breeding timing patterns
- ✅ Colony site fidelity across years
- ✅ Range shifts (colonies gained/lost)

**What You CANNOT Analyze:**
- ❌ Individual bird migration routes
- ❌ Wintering grounds
- ❌ Stopover sites
- ❌ Real-time movement tracking

---

## Migration-Related Queries

### 1. Species Presence Over Time

**Question:**
```
Which species were present in 2010 but not in 2021?
```

**Analysis**: May indicate range shifts, population declines, or site abandonment

### 2. Seasonal Patterns

**Question:**
```
When do Brown Pelicans typically arrive at colonies?
```

**Method**: Compare observation dates across years

### 3. Colony Site Fidelity

**Question:**
```
Which species consistently return to the same colonies?
```

**Interpretation**: High fidelity = strong site attachment

---

## Example Queries

### Species Turnover

```sql
-- Species appearing in different years
SELECT
    species_code,
    COUNT(DISTINCT year) as years_present,
    MIN(year) as first_seen,
    MAX(year) as last_seen
FROM observations
WHERE species_code != '' AND species_code IS NOT NULL
GROUP BY species_code
ORDER BY years_present DESC;
```

### New Species at Colonies

```sql
-- Species that appeared after 2010
SELECT
    o.colony_name,
    o.species_code,
    MIN(o.year) as first_appearance
FROM observations o
WHERE o.species_code != ''
AND o.species_code NOT IN (
    SELECT DISTINCT species_code
    FROM observations
    WHERE year = 2010
)
GROUP BY o.colony_name, o.species_code
ORDER BY first_appearance, o.colony_name;
```

---

## Interpretation Guide

### Presence/Absence Patterns

**Consistent Presence (7/7 years):**
- Resident or very faithful migrants
- Examples: LAGU, BRPE in core colonies

**Sporadic Presence (1-3 years):**
- Vagrants, colonization attempts, or survey gaps
- Requires careful interpretation

**Declining Presence:**
- May indicate habitat degradation
- Population decline
- Range contraction

---

## For True Migration Analysis

### Recommended Datasets

To study actual migration routes, use:
1. **eBird** - Citizen science observations
2. **USGS Bird Banding Lab** - Band recovery data
3. **Movebank** - GPS tracking data
4. **MOTUS** - Automated radio telemetry

### Complementary Analysis

Use THIS dataset + migration data:
- Identify breeding populations (this data)
- Track movements between sites (migration data)
- Connect breeding success to migration patterns

---

**For more examples, see [EXAMPLES.md](EXAMPLES.md)**
