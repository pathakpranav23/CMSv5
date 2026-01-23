
import sys
import os
import subprocess

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def seed_even_semesters():
    print("--- Seeding BCA Even Semesters (2, 4, 6) ---")
    
    # Define file paths relative to this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "subject_data")
    
    files = [
        os.path.join(data_dir, "BCA-Sem-2-Subject-list-with-code-1.xlsx"),
        os.path.join(data_dir, "BCA-Sem-4-Subject-list-with-code-1.xlsx"),
        os.path.join(data_dir, "BCA-Sem-6-Subject-list-with-code-1.xlsx")
    ]
    
    import_script = os.path.join(base_dir, "import_subjects.py")
    
    for f in files:
        if not os.path.exists(f):
            print(f"ERROR: File not found: {f}")
            continue
            
        print(f"\nProcessing: {os.path.basename(f)}")
        # Call the existing import script
        try:
            subprocess.run(["python", import_script, f], check=True)
            print("  -> Success")
        except subprocess.CalledProcessError as e:
            print(f"  -> FAILED: {e}")

if __name__ == "__main__":
    seed_even_semesters()
