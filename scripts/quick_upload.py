#!/usr/bin/env python3
"""Quick upload to Supabase."""
import os
import pandas as pd
from supabase import create_client

SUPABASE_URL = "https://pabegzmewqavkqndmclg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBhYmVnem1ld3FhdmtxbmRtY2xnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY4NjA3NTUsImV4cCI6MjA4MjQzNjc1NX0.uzlx6XpH5JkJIuO0uWfqeAD6woa1gI9fNlVrk0AyXU4"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

chunks_dir = "data/supabase_chunks"
batch_size = 500  # Smaller batches for stability

files = sorted([f for f in os.listdir(chunks_dir) if f.endswith('.csv')])
print(f"Found {len(files)} files to upload")

for file_num, filename in enumerate(files, 1):
    filepath = os.path.join(chunks_dir, filename)
    print(f"\n[{file_num}/{len(files)}] Uploading {filename}...")
    
    df = pd.read_csv(filepath)
    total = len(df)
    uploaded = 0
    
    for i in range(0, total, batch_size):
        batch = df.iloc[i:i+batch_size].to_dict('records')
        try:
            supabase.table('shots').insert(batch).execute()
            uploaded += len(batch)
            pct = uploaded / total * 100
            print(f"  Progress: {pct:.1f}% ({uploaded:,}/{total:,})", end='\r')
        except Exception as e:
            print(f"\n  Error at batch {i}: {e}")
            continue
    
    print(f"\n  ✅ Done: {uploaded:,} rows uploaded")

print("\n🎉 All uploads complete!")

# Verify count
result = supabase.table("shots").select("*", count="exact").limit(1).execute()
print(f"📊 Total shots in Supabase: {result.count:,}")

