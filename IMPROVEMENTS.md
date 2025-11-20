# Classification System Improvements

## Problem Analysis
**Before improvements:**
- 52% of tracks (1336/2587) classified as generic "World" with low confidence (0.5)
- 49% of all tracks had low confidence (<0.6)
- Heavy dependency on LLM for all classifications
- No deterministic rules for obvious cases
- LLM prompt lacked clarity and examples

## Solution: Hybrid Classification System

### 1. Rule-Based Pre-Classifier (`rule_classifier.py`)
**New file** that handles obvious cases deterministically WITHOUT LLM calls.

**Features:**
- **Comprehensive artist databases** (400+ artists across all categories)
  - 35+ Punjabi artists (Sidhu Moose Wala, Karan Aujla, AP Dhillon...)
  - 15+ Hindi Party artists (Badshah, Honey Singh...)
  - 25+ Hindi Melodic artists (Arijit Singh, A.R. Rahman...)
  - 24+ English Pop artists (The Weeknd, Dua Lipa...)
  - 32+ English Hip-Hop artists (Drake, Eminem, Travis Scott...)
  - 19+ English R&B artists (Frank Ocean, SZA...)
  - 22+ English Rock artists (Arctic Monkeys, Linkin Park...)
  - Specialized: Phonk, Gym Hype, Lofi, Soundtrack, Oldies artists

- **Genre-based classification** using Spotify genre tags
  - Direct mapping: "phonk" → Gym-Phonk (95% confidence)
  - Pattern matching: "bollywood + dance" → Hindi Party
  - Language detection: "k-pop", "french", "latin" → World

- **Mood/vibe detection** (highest priority)
  - Sad keywords: heartbreak, lonely, tears, pain, miss
  - Phonk keywords: drift, cowbell, aggressive, sigma
  - Gym keywords: workout, beast mode, hype, rage
  - Chill keywords: lofi, ambient, relax, study, calm

- **Language pattern recognition**
  - Punjabi patterns: jatt, pind, yaari, gaddi, dhol
  - Hindi patterns: hai, mera, tera, dil, pyaar

- **Confidence boosting system**
  - When LLM and rules agree → use higher confidence
  - When rules are very confident (≥90%) → override LLM

**Expected Impact:** 60-70% of tracks classified by rules alone, saving LLM costs and improving accuracy.

### 2. Enhanced LLM Integration
**Modified `llm_classifier.py`** for hybrid approach.

**Workflow:**
```
1. Run rule-based classification first (fast, deterministic)
   ↓
2. Only send ambiguous cases to LLM (30-40% of tracks)
   ↓
3. Apply confidence boosting when rules + LLM agree
```

**Benefits:**
- 60-70% cost reduction (fewer LLM calls)
- Faster processing (rules are instant)
- Higher accuracy for obvious cases
- LLM focuses on genuinely ambiguous tracks

### 3. Improved LLM Prompt Engineering
**Completely rewritten prompt** with:

**Better Structure:**
- Clear decision tree (check genres → mood → artist → title → default)
- Explicit examples for each category
- Confidence guidelines (0.95 = perfect genre match, 0.90 = known artist, etc.)

**Category Improvements:**
- Added specific song examples: "295" (Punjabi), "Blinding Lights" (Pop), "Lucid Dreams" (Sad)
- Genre tag mappings: "punjabi/bhangra" → Punjabi, "k-pop/french" → World
- Clear distinction between "English - Hip-Hop" and "Gym - Hype"

**Critical Rules Emphasized:**
- ✅ Sad mood OVERRIDES language
- ✅ "World" is ONLY non-English/Hindi/Punjabi
- ✅ Use genres as primary signal
- ✅ Avoid generic "World" classification

## Expected Improvements

### Accuracy
- **Before:** 52% misclassified as "World"
- **After:** Expected <15% "World" (only true foreign language songs)
- **Rule accuracy:** 95%+ for known artists
- **Hybrid accuracy:** 85%+ overall

### Confidence Distribution
- **Before:** 49% low confidence (<0.6)
- **After:** Expected 70%+ high confidence (>0.8)
- Rule-based: 85-95% confidence
- LLM with boosting: 80-90% confidence

### Performance
- **LLM calls reduced by 60-70%** (only ambiguous cases)
- **Processing time reduced** (rules are instantaneous)
- **Cost savings:** 60-70% reduction in API usage

### User Experience
- More consistent classifications
- Higher confidence scores
- Better handling of regional music
- Fewer generic "World" classifications

## Future Enhancements

### For Local/Offline Classification
1. **Expand artist databases** as you encounter new artists
   - Easy to add: just update `RuleClassifier` artist sets
   - No retraining needed

2. **Add user feedback loop**
   - Learn from corrections
   - Build custom artist mappings
   - Improve over time

3. **Language detection library** (optional)
   - Use `langdetect` or `polyglot` for title language
   - Higher accuracy for foreign songs

4. **Audio analysis** (when available)
   - Tempo, energy, valence (if you get Extended Quota)
   - BPM-based classification (phonk = 140-180 BPM)

5. **Local ML model** (future goal)
   - Train on your classified dataset
   - Use audio features + metadata
   - Zero API dependency

## How to Expand Artist Database

Edit `rule_classifier.py` and add artists to the appropriate sets:

```python
PUNJABI_ARTISTS = {
    'sidhu moose wala', 'karan aujla', 'ap dhillon',
    # Add new artist here:
    'new punjabi artist',
}
```

The rule classifier will immediately use them with 95% confidence.

## Testing Recommendations

1. **Backup current classifications:**
   ```bash
   cp .cache/classifications.json .cache/classifications_backup.json
   ```

2. **Clear cache and re-classify:**
   ```bash
   rm .cache/classifications.json
   streamlit run app.py
   ```

3. **Compare results:**
   - Check "World" percentage (should drop from 52% to <15%)
   - Check confidence distribution (should improve significantly)
   - Spot-check specific artists you know

4. **Monitor LLM usage:**
   - Watch console output: "X tracks classified by rules (Y%)"
   - Should see 60-70% rule-based classification

## Configuration

Both systems use centralized config:
- `BATCH_SIZE=100` (songs per LLM request)
- `PARALLEL_WORKERS=8` (concurrent requests)

All artist databases and rules in `rule_classifier.py` are easily expandable.
