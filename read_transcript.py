# read_transcript.py
from config.db_config import SessionLocal
from database.models import Chunk, Source

db = SessionLocal()
youtube_source = db.query(Source).filter(Source.domain == 'youtube.com').first()
chunks = db.query(Chunk).filter(Chunk.source_id == youtube_source.id).order_by(Chunk.seq).all()

print("YOUTUBE VIDEO TRANSCRIPT - INDORE BUILDING COLLAPSE")
print("=" * 80)
for i, chunk in enumerate(chunks, 1):
    print(f"\n--- Chunk {i} ---")
    print(chunk.text)

db.close() 