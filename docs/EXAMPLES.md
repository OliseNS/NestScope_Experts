# Example Queries

50+ example questions organized by analysis type.

---

## Bird Population Queries

### Species Observations

```
Which species were observed most frequently?
How many Brown Pelican observations are there?
Show me all Black Skimmer (BLSK) observations
List all species observed at Breton Island
What species have more than 500 observations?
```

### Colony-Specific

```
What species were seen at Chandeleur Islands?
Show observations from Long Bay Island
List all colonies in Louisiana
Which colonies in Texas had Royal Terns?
Show me the top 5 colonies by observation count
```

### Temporal

```
How many observations per year?
Show observations from 2015 to 2021
What species were present in 2010 but not 2021?
Compare species counts 2010 vs 2021
Which year had the most observations?
```

---

## Coastal Erosion Queries

### Colony Loss

```
Which colonies were active in 2010 but disappeared by 2021?
What percentage of 2010 colonies are still active?
List inactive colonies from colony_inventory
How many colonies were lost in Louisiana?
Show colonies that only appeared once
```

### Habitat Change

```
Show colonies with notes mentioning erosion
Which colonies experienced flooding?
Show observations with vegetation loss
List colonies with overwash events
How did habitats change at Cat Bay South Island?
```

### Regional Patterns

```
Which barrier islands show the most degradation?
What states had the highest colony loss rates?
Show erosion patterns in Mississippi colonies
Which ecoregions lost the most colonies?
List colonies lost after 2015
```

---

## Environmental Impact Queries

### Oil Spill

```
What colonies had oil present in 2010?
Show all observations with oil noted
Compare oil-affected vs non-affected colonies
How many species were in oil-impacted colonies?
Did oil-affected colonies recover by 2021?
```

### Storm Damage

```
Which colonies were affected by Hurricane Isaac?
Show observations mentioning storms or hurricanes
List colonies with flood damage in notes
How did storms affect Texas colonies?
Compare colony counts before and after Isaac
```

### Habitat Types

```
What are the most common habitat types?
Show colonies with marsh habitats
Which habitat types decreased over time?
List colonies by primary habitat
How many colonies have mangrove habitats?
```

---

## Species-Specific Queries

### Laughing Gull (LAGU)

```
How many Laughing Gull observations per year?
Which colonies have the most LAGU?
Show LAGU observations with breeding notes
Compare LAGU presence 2010 vs 2021
What habitats do Laughing Gulls prefer?
```

### Brown Pelican (BRPE)

```
Show Brown Pelican colonies in Louisiana
How did BRPE populations change over time?
Which colonies had BRPE nesting?
Show BRPE observations with chick counts
Did oil affect Brown Pelican colonies?
```

### Terns (ROYT, SATE, CATE)

```
Show all Royal Tern colonies
Compare ROYT vs SATE observations
Which colonies have multiple tern species?
Show tern observations from 2018
Did tern populations recover after 2010?
```

---

## Advanced Analytical Queries

### Population Trends

```
Which species showed population increases?
What colonies had declining observations?
Show species diversity changes over time
Compare nesting success across years
Which species disappeared from colonies?
```

### Geographic Analysis

```
Compare colonies in Barataria Bay vs Biloxi Sound
Show latitudinal distribution of species
Which geo_regions had the most observations?
List colonies within 10km of each other
Show state-by-state species counts
```

### Data Quality

```
Which observations have complete coordinates?
Show records with missing species codes
List observations with no notes
Which colonies have observations in all years?
Show data completeness by year
```

---

## Multi-Table Joins

### Observations + Species

```
Show observations with full species names
List Brown Pelicans with scientific names
Which Great Egrets were observed in 2010?
```

### Observations + Colony Inventory

```
Show inactive colonies that still have observations
List observations from colonies marked as lost
Compare active vs inactive colony data
```

### All Tables Combined

```
Show complete data for Chandeleur Islands
List all information about LAGU colonies
Full profile for Cat Bay South Island
```

---

## Statistical Queries

### Aggregations

```
Average observations per colony
Total nest counts by species
Maximum bird count per colony
Sum of observations per state
```

### Distributions

```
Distribution of observations by year
Species richness per colony
Observation frequency by month
Geographic spread of colonies
```

### Comparisons

```
Compare pre-2015 vs post-2015 observations
Active vs inactive colony statistics
Oil vs non-oil colony differences
Gulf vs Atlantic coast comparisons
```

---

## Research-Focused Queries

### Conservation

```
Which endangered species are tracked?
Show colonies needing protection
List high-biodiversity colonies
Identify restoration priorities
```

### Climate Change

```
Show evidence of habitat shifts
Track vegetation loss over time
Document sea level rise impacts
Identify climate-vulnerable colonies
```

### Monitoring

```
Which colonies need resurvey?
Show gaps in survey coverage
List unmonitored regions
Track survey effort over time
```

---

## Quick Reference Commands

### Database Statistics
```
stats
```

### Example Questions
```
examples
```

### Exit
```
quit
exit
q
```

---

## Tips for Complex Queries

### Combine Multiple Criteria

```
Show Louisiana BRPE colonies from 2010 with oil and more than 50 nests
```

### Use Ranges

```
List colonies with 100-500 total observations
Show species observed between 2015 and 2018
```

### Negative Queries

```
Which colonies never had oil present?
Show years with no observations at Breton Island
List species not seen after 2015
```

---

## For More Information

- **[USAGE.md](USAGE.md)** - How to ask questions
- **[DATA_SCHEMA.md](DATA_SCHEMA.md)** - Database structure
- **[EROSION_ANALYSIS.md](EROSION_ANALYSIS.md)** - Erosion research guide
- **[MIGRATION_ANALYSIS.md](MIGRATION_ANALYSIS.md)** - Migration patterns

---

**Try these queries in the chatbot to explore the data!**
