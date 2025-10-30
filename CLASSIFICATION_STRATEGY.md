# Classification Improvement Strategy

## Current Issues
- ❌ "Gaand Mein Danda" → Punjabi (should be Hindi/Misc)
- ❌ "AARAMBH HAI PRACHAND" → Hindi (correct but low confidence)
- ❌ Many collaborations misclassified
- ❌ Not using album names (strong signals)
- ❌ Not using track popularity/markets effectively

## **NEW APPROACH: Multi-Source Decision Tree**

### Priority 1: Artist Database (Exact Match)
- 90+ known artists
- **Enhancement**: Add album patterns too
  - "Judwaa 2", "Student of the Year" → Hindi/Bollywood
  - "Still Rolling", "King Shit" → Punjabi

### Priority 2: Title + Album Analysis
- **Combine both** for stronger signals
- Album: "Coke Studio Bharat" → likely Hindi/Punjabi
- Album: "Leo (Original Motion Picture Soundtrack)" → likely Hindi

### Priority 3: Year + Artist Pattern
- Pre-1995 + South Asian → Oldies
- 2020+ + Punjabi words → Punjabi (new wave)

### Priority 4: Language Detection Library
- **Use `langdetect` more aggressively**
- Detect from: Title + Album + Artist names combined

### Priority 5: LLM with Enhanced Context
- Pass: Artist + Album + Year + Title + Keywords detected

## **Implementation Plan**

### Phase 1: Better Rule-Based Classification (80% accuracy)
```python
def smart_classify(track):
    # 1. Check artist DB (exact)
    # 2. Check album patterns
    # 3. Detect language from title+album
    # 4. Check year + patterns
    # 5. Use title keywords (expanded)
    # Only use LLM if confidence < 0.7
```

### Phase 2: Album Intelligence
```python
ALBUM_PATTERNS = {
    'Punjabi': ['coke studio', 'punjabi', 'pind', 'jatt'],
    'Hindi': ['bollywood', 'soundtrack', 'bollywood hits', 'yrf'],
    'Oldies': ['golden hits', 'evergreen', 'classic']
}
```

### Phase 3: Better Language Detection
```python
# Detect from combined text
text = f"{title} {album} {primary_artist}"
lang = detect(text)  # More accurate with more text
```

### Phase 4: Confidence Scoring System
```python
confidence = 0.0
if artist_match: confidence += 0.4
if album_match: confidence += 0.2
if language_match: confidence += 0.2
if title_keywords: confidence += 0.1
if year_match: confidence += 0.1
# Use LLM only if confidence < 0.7
```

## Expected Improvements
- **Punjabi**: 85% → 92% (album + better keywords)
- **Hindi**: 75% → 88% (Bollywood albums + soundtracks)
- **Oldies**: 90% → 95% (year + artist + album)
- **English**: 70% → 85% (better artist DB)
- **Misc**: 30% → 15% (fewer fallbacks)

## Libraries to Consider
1. ✅ **langdetect** (already have) - use MORE aggressively
2. ✅ **Spotify API** (already have) - USE album field!
3. ❌ **polyglot** - overkill, needs NLP models
4. ❌ **googletrans** - API limits, slow
5. ✅ **regex patterns** - for album/title parsing

## Next Steps
1. Implement album pattern matching
2. Enhanced language detection (title + album combined)
3. Confidence-based LLM fallback (only when needed)
4. Add more artist patterns from misclassifications
