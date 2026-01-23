
import os
import shutil
import zipfile
import datetime
import time

def create_backup():
    backup_dir = os.path.join(os.getcwd(), "_BACKUPS")
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Database Backup
    db_path = os.path.join(os.getcwd(), "cms.db")
    if os.path.exists(db_path):
        db_backup_name = f"cms.db.backup_local_{timestamp}"
        shutil.copy2(db_path, os.path.join(backup_dir, db_backup_name))
        print(f"Database backed up to: {db_backup_name}")
    
    # 2. Codebase Backup (excluding heavy/irrelevant folders)
    zip_name = f"codebase_backup_{timestamp}.zip"
    zip_path = os.path.join(backup_dir, zip_name)
    
    print("Creating codebase zip...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(os.getcwd()):
            # Exclude directories
            dirs[:] = [d for d in dirs if d not in [
                '_BACKUPS', '__pycache__', 'venv', '.git', '.idea', 'node_modules', 'instance', 'DATA FOR IMPORT EXPORT'
            ]]
            
            for file in files:
                if file.endswith(('.pyc', '.pyo', '.pyd', '.db', '.sqlite', '.zip', '.7z', '.rar')):
                    continue
                
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.getcwd())
                zipf.write(file_path, arcname)
    
    print(f"Codebase backed up to: {zip_name}")

def list_changes_since(date_str):
    # date_str format: YYYY-MM-DD
    cutoff_time = datetime.datetime.strptime(date_str, "%Y-%m-%d").timestamp()
    
    print(f"\nFiles modified since {date_str}:")
    print("-" * 50)
    
    changed_files = []
    
    for root, dirs, files in os.walk(os.getcwd()):
        # Exclude directories
        dirs[:] = [d for d in dirs if d not in [
            '_BACKUPS', '__pycache__', 'venv', '.git', '.idea', 'node_modules', 'instance', 'DATA FOR IMPORT EXPORT'
        ]]
        
        for file in files:
            if file.endswith(('.pyc', '.pyo', '.pyd', '.db', '.sqlite', '.zip')):
                continue
                
            file_path = os.path.join(root, file)
            try:
                mtime = os.path.getmtime(file_path)
                if mtime > cutoff_time:
                    rel_path = os.path.relpath(file_path, os.getcwd())
                    # exclude the backup script itself if created just now
                    if "backup_and_diff.py" in rel_path:
                        continue
                    
                    mod_date = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
                    changed_files.append((rel_path, mod_date))
            except OSError:
                continue
                
    # Sort by modification time (newest first)
    changed_files.sort(key=lambda x: x[1], reverse=True)
    
    if not changed_files:
        print("No files modified since this date.")
    else:
        for path, mod_date in changed_files:
            print(f"[{mod_date}] {path}")

if __name__ == "__main__":
    create_backup()
    # Check changes since Jan 17, 2026 (last backup date)
    list_changes_since("2026-01-17")
