"""Manager for manual review of classifications."""
import json
import os
from datetime import datetime
from typing import Dict, List

class ReviewManager:
    """Manages the review process for classified tracks."""
    
    REVIEW_DIR = ".review"
    REVIEW_FILE = os.path.join(REVIEW_DIR, "classification_review.json")
    
    @classmethod
    def ensure_review_dir(cls):
        """Ensure review directory exists."""
        os.makedirs(cls.REVIEW_DIR, exist_ok=True)
    
    @classmethod
    def save_for_review(cls, categorized_tracks: Dict[str, List[Dict]], source_name: str) -> str:
        """
        Save categorized tracks for manual review.
        
        Args:
            categorized_tracks: Dictionary of categories to track lists
            source_name: Name of the source (playlist/liked songs)
            
        Returns:
            Path to the review file
        """
        cls.ensure_review_dir()
        
        # Calculate stats
        total_tracks = sum(len(tracks) for tracks in categorized_tracks.values())
        
        review_data = {
            "timestamp": datetime.now().isoformat(),
            "source": source_name,
            "total_tracks": total_tracks,
            "approved": False,
            "categories": {}
        }
        
        for category, tracks in categorized_tracks.items():
            review_data["categories"][category] = {
                "count": len(tracks),
                "tracks": tracks
            }
            
        with open(cls.REVIEW_FILE, 'w', encoding='utf-8') as f:
            json.dump(review_data, f, indent=2, ensure_ascii=False)
            
        return cls.REVIEW_FILE
    
    @classmethod
    def is_approved(cls) -> bool:
        """Check if the review file has been approved."""
        if not os.path.exists(cls.REVIEW_FILE):
            return False
            
        try:
            with open(cls.REVIEW_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("approved", False)
        except Exception:
            return False
            
    @classmethod
    def load_review(cls) -> Dict:
        """Load the review data."""
        if not os.path.exists(cls.REVIEW_FILE):
            raise FileNotFoundError("No review file found")
            
        with open(cls.REVIEW_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
