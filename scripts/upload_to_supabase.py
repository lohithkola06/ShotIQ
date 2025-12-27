#!/usr/bin/env python3
"""
Upload NBA shot data to Supabase.
Run: python scripts/upload_to_supabase.py
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from supabase import create_client

# Get these from Supabase Dashboard -> Settings -> API
SUPABASE_URL = os.environ.get("SUPABASE_URL", "YOUR_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "YOUR_SUPABASE_ANON_KEY")

BATCH_SIZE = 5000  # Upload in batches to avoid timeouts


def main():
    print("=" * 60)
    print("Uploading NBA Shot Data to Supabase")
    print("=" * 60)
    
    # Load the clean data
    from src.data_loader import load_clean
    print("\n📊 Loading clean shot data...")
    df = load_clean()
    print(f"   Loaded {len(df):,} shots")
    
    # Select only needed columns and rename to lowercase
    columns = {
        "PLAYER_NAME": "player_name",
        "TEAM_NAME": "team_name", 
        "LOC_X": "loc_x",
        "LOC_Y": "loc_y",
        "SHOT_MADE_FLAG": "shot_made_flag",
        "SHOT_DISTANCE": "shot_distance",
        "SHOT_TYPE": "shot_type",
        "ACTION_TYPE": "action_type",
        "YEAR": "year",
    }
    
    df = df[list(columns.keys())].rename(columns=columns)
    print(f"   Selected columns: {list(df.columns)}")
    
    # Connect to Supabase
    print(f"\n🔌 Connecting to Supabase...")
    if "YOUR_SUPABASE" in SUPABASE_URL:
        print("❌ Error: Set SUPABASE_URL and SUPABASE_KEY environment variables")
        print("   export SUPABASE_URL='https://xxx.supabase.co'")
        print("   export SUPABASE_KEY='your-anon-key'")
        sys.exit(1)
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("   ✅ Connected!")
    
    # Upload in batches
    print(f"\n📤 Uploading {len(df):,} shots in batches of {BATCH_SIZE}...")
    
    total_batches = (len(df) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for i in range(0, len(df), BATCH_SIZE):
        batch = df.iloc[i:i+BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        
        # Convert to list of dicts
        records = batch.to_dict('records')
        
        # Insert batch
        try:
            supabase.table("shots").insert(records).execute()
            print(f"   Batch {batch_num}/{total_batches} uploaded ({len(records)} records)")
        except Exception as e:
            print(f"   ❌ Batch {batch_num} failed: {e}")
            # Continue with next batch
            continue
    
    print("\n" + "=" * 60)
    print("✅ Upload complete!")
    print("=" * 60)
    
    # Verify count
    result = supabase.table("shots").select("*", count="exact").limit(1).execute()
    print(f"\n📊 Total shots in Supabase: {result.count:,}")


if __name__ == "__main__":
    main()

