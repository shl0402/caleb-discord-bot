"""
Script to clean up old downloaded music files from the bot directory
"""
import os
import glob

# Patterns of files to delete
patterns = [
    'youtube-*.mp4',
    'youtube-*.webm',
    'youtube-*.m4a',
    'youtube-*.opus',
    '*.part',
    '*.ytdl'
]

deleted_count = 0
total_size = 0

print("Scanning for downloaded music files...")

for pattern in patterns:
    for file_path in glob.glob(pattern):
        try:
            file_size = os.path.getsize(file_path)
            os.remove(file_path)
            deleted_count += 1
            total_size += file_size
            print(f"Deleted: {file_path} ({file_size / 1024 / 1024:.2f} MB)")
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")

if deleted_count > 0:
    print(f"\n✅ Cleaned up {deleted_count} file(s)")
    print(f"💾 Freed {total_size / 1024 / 1024:.2f} MB of disk space")
else:
    print("✅ No downloaded files found to clean up")
