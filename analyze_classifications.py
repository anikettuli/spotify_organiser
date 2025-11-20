"""Utility to analyze and compare classification results."""
import json
import sys
from collections import Counter, defaultdict


def analyze_classifications(filepath: str):
    """Analyze classification distribution and confidence."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    categories = Counter()
    confidence_ranges = {'very_low': 0, 'low': 0, 'medium': 0, 'high': 0, 'very_high': 0}
    confidence_by_category = defaultdict(list)
    
    for track_id, info in data.items():
        cat = info['category']
        conf = info['confidence']
        
        categories[cat] += 1
        confidence_by_category[cat].append(conf)
        
        if conf < 0.5:
            confidence_ranges['very_low'] += 1
        elif conf < 0.7:
            confidence_ranges['low'] += 1
        elif conf < 0.8:
            confidence_ranges['medium'] += 1
        elif conf < 0.9:
            confidence_ranges['high'] += 1
        else:
            confidence_ranges['very_high'] += 1
    
    total = len(data)
    
    print(f"\n{'='*60}")
    print(f"CLASSIFICATION ANALYSIS: {filepath}")
    print(f"{'='*60}\n")
    
    print(f"📊 Total Tracks: {total}\n")
    
    print("📈 Category Distribution:")
    print("-" * 60)
    for cat, count in categories.most_common():
        pct = count / total * 100
        avg_conf = sum(confidence_by_category[cat]) / len(confidence_by_category[cat])
        bar = '█' * int(pct / 2)
        print(f"{cat:30s} {count:4d} ({pct:5.1f}%) avg_conf={avg_conf:.2f} {bar}")
    
    print(f"\n🎯 Confidence Distribution:")
    print("-" * 60)
    print(f"Very High (≥0.90): {confidence_ranges['very_high']:4d} ({confidence_ranges['very_high']/total*100:5.1f}%)")
    print(f"High (0.80-0.89):  {confidence_ranges['high']:4d} ({confidence_ranges['high']/total*100:5.1f}%)")
    print(f"Medium (0.70-0.79): {confidence_ranges['medium']:4d} ({confidence_ranges['medium']/total*100:5.1f}%)")
    print(f"Low (0.50-0.69):   {confidence_ranges['low']:4d} ({confidence_ranges['low']/total*100:5.1f}%)")
    print(f"Very Low (<0.50):  {confidence_ranges['very_low']:4d} ({confidence_ranges['very_low']/total*100:5.1f}%)")
    
    # Key metrics
    world_count = categories.get('World', 0)
    world_pct = world_count / total * 100
    high_conf_count = confidence_ranges['high'] + confidence_ranges['very_high']
    high_conf_pct = high_conf_count / total * 100
    
    print(f"\n🔑 Key Metrics:")
    print("-" * 60)
    print(f"'World' classifications: {world_count:4d} ({world_pct:5.1f}%) {'⚠️ HIGH' if world_pct > 20 else '✅ Good'}")
    print(f"High confidence (≥0.80): {high_conf_count:4d} ({high_conf_pct:5.1f}%) {'✅ Excellent' if high_conf_pct > 70 else '⚠️ Needs improvement'}")
    print()
    

def compare_classifications(before_file: str, after_file: str):
    """Compare two classification results."""
    with open(before_file, 'r') as f:
        before = json.load(f)
    with open(after_file, 'r') as f:
        after = json.load(f)
    
    # Track changes
    changed = 0
    confidence_improved = 0
    world_to_specific = 0
    specific_to_world = 0
    
    category_transitions = defaultdict(lambda: defaultdict(int))
    
    common_ids = set(before.keys()) & set(after.keys())
    
    for track_id in common_ids:
        before_cat = before[track_id]['category']
        after_cat = after[track_id]['category']
        before_conf = before[track_id]['confidence']
        after_conf = after[track_id]['confidence']
        
        if before_cat != after_cat:
            changed += 1
            category_transitions[before_cat][after_cat] += 1
            
            if before_cat == 'World' and after_cat != 'World':
                world_to_specific += 1
            elif before_cat != 'World' and after_cat == 'World':
                specific_to_world += 1
        
        if after_conf > before_conf + 0.05:  # At least 5% improvement
            confidence_improved += 1
    
    print(f"\n{'='*60}")
    print(f"COMPARISON: BEFORE vs AFTER")
    print(f"{'='*60}\n")
    
    print(f"📊 Tracks Analyzed: {len(common_ids)}\n")
    
    print(f"🔄 Category Changes:")
    print("-" * 60)
    print(f"Total changed: {changed} ({changed/len(common_ids)*100:.1f}%)")
    print(f"'World' → Specific: {world_to_specific} ✅")
    print(f"Specific → 'World': {specific_to_world} {'⚠️' if specific_to_world > world_to_specific else '✅'}")
    print(f"Confidence improved: {confidence_improved} ({confidence_improved/len(common_ids)*100:.1f}%)")
    
    if category_transitions:
        print(f"\n📊 Top Category Transitions:")
        print("-" * 60)
        all_transitions = []
        for from_cat, to_cats in category_transitions.items():
            for to_cat, count in to_cats.items():
                all_transitions.append((count, from_cat, to_cat))
        
        for count, from_cat, to_cat in sorted(all_transitions, reverse=True)[:10]:
            print(f"{from_cat:25s} → {to_cat:25s} ({count:3d} tracks)")
    
    print()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python analyze_classifications.py <classifications_file>")
        print("  python analyze_classifications.py <before_file> <after_file>")
        sys.exit(1)
    
    if len(sys.argv) == 2:
        analyze_classifications(sys.argv[1])
    else:
        analyze_classifications(sys.argv[1])
        analyze_classifications(sys.argv[2])
        compare_classifications(sys.argv[1], sys.argv[2])
