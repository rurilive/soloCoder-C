import os
import shutil

BASE_UPLOAD_DIR = "./uploads"
USER_ID = 1

print(f"开始迁移照片文件到用户目录 (user_id={USER_ID})...")

user_dir = os.path.join(BASE_UPLOAD_DIR, str(USER_ID))
user_thumbnails_dir = os.path.join(user_dir, "thumbnails")
old_thumbnails_dir = os.path.join(BASE_UPLOAD_DIR, "thumbnails")

os.makedirs(user_dir, exist_ok=True)
os.makedirs(user_thumbnails_dir, exist_ok=True)

migrated_count = 0
skipped_count = 0

if os.path.exists(old_thumbnails_dir):
    for filename in os.listdir(old_thumbnails_dir):
        old_path = os.path.join(old_thumbnails_dir, filename)
        if os.path.isfile(old_path):
            new_path = os.path.join(user_thumbnails_dir, filename)
            if not os.path.exists(new_path):
                shutil.copy2(old_path, new_path)
                print(f"  复制缩略图: {filename}")
                migrated_count += 1
            else:
                print(f"  跳过已存在的缩略图: {filename}")
                skipped_count += 1

for filename in os.listdir(BASE_UPLOAD_DIR):
    old_path = os.path.join(BASE_UPLOAD_DIR, filename)
    if os.path.isfile(old_path) and not filename.startswith('.'):
        new_path = os.path.join(user_dir, filename)
        if not os.path.exists(new_path):
            shutil.copy2(old_path, new_path)
            print(f"  复制照片: {filename}")
            migrated_count += 1
        else:
            print(f"  跳过已存在的照片: {filename}")
            skipped_count += 1

print(f"\n照片文件迁移完成:")
print(f"  - 复制了 {migrated_count} 个文件")
print(f"  - 跳过了 {skipped_count} 个已存在的文件")
print(f"  - 目标目录: {user_dir}")
