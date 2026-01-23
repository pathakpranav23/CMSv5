
import os
import datetime

def list_changes_since(date_str):
    cutoff_time = datetime.datetime.strptime(date_str, "%Y-%m-%d").timestamp()
    
    print(f"Files modified since {date_str} (excluding backups/temp):")
    
    changed_files = []
    
    for root, dirs, files in os.walk(os.getcwd()):
        # Exclude directories
        dirs[:] = [d for d in dirs if d not in [
            '_BACKUPS', '__pycache__', 'venv', '.git', '.idea', 'node_modules', 'instance', 
            'DATA FOR IMPORT EXPORT', '_temp_restore', '_docx_blueprint'
        ]]
        
        for file in files:
            if file.endswith(('.pyc', '.pyo', '.pyd', '.db', '.sqlite', '.zip', '.7z', '.rar')):
                continue
                
            file_path = os.path.join(root, file)
            try:
                mtime = os.path.getmtime(file_path)
                if mtime > cutoff_time:
                    rel_path = os.path.relpath(file_path, os.getcwd())
                    # exclude this script
                    if "list_updates.py" in rel_path or "backup_and_diff.py" in rel_path:
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
    list_changes_since("2026-01-17")
