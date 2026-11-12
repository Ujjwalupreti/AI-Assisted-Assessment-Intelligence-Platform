import os
import json
import shutil

base_path = r"c:\Users\Hp\Downloads\PRoject\ai_project_copy"
json_path = os.path.join(base_path, "scan_results.json")

def execute():
    if not os.path.exists(json_path):
        print("scan_results.json not found!")
        return

    with open(json_path, 'r') as f:
        data = json.load(f)

    # 1. Delete duplicates of .jpeg files
    for hash_val, files in data.get('duplicates', {}).items():
        # Only process if they are jpeg files
        if len(files) > 1 and all(f.endswith('.jpeg') for f in files):
            # Keep the first one, delete the rest
            keep_file = files[0]
            delete_files = files[1:]
            for f in delete_files:
                if os.path.exists(f):
                    print(f"Deleting duplicate image: {f}")
                    os.remove(f)
                    
    # 2. Delete useless files (excluding scan_results.json which we are reading now, and we'll delete it later)
    for f in data.get('useless_files', []):
        if os.path.exists(f):
            print(f"Deleting useless file: {f}")
            os.remove(f)
            
    # 3. Organize loose scripts
    migrations_dir = os.path.join(base_path, "backend", "scripts", "migrations")
    tests_dir = os.path.join(base_path, "backend", "tests")
    scripts_dir = os.path.join(base_path, "backend", "scripts")
    
    os.makedirs(migrations_dir, exist_ok=True)
    os.makedirs(tests_dir, exist_ok=True)
    os.makedirs(scripts_dir, exist_ok=True)
    
    for f in data.get('one_off_scripts_to_organize', []):
        if not os.path.exists(f):
            continue
            
        filename = os.path.basename(f)
        
        if filename.startswith('update_schema'):
            dest = os.path.join(migrations_dir, filename)
        elif filename.startswith('test_') or filename == 'scratch_qis_test.py':
            dest = os.path.join(tests_dir, filename)
        else:
            dest = os.path.join(scripts_dir, filename)
            
        print(f"Moving {filename} to {dest}")
        shutil.move(f, dest)

    # Finally, delete scan_project.py and scan_results.json
    scan_script = os.path.join(base_path, "scan_project.py")
    if os.path.exists(scan_script):
        print(f"Deleting {scan_script}")
        os.remove(scan_script)
        
    print(f"Deleting {json_path}")
    os.remove(json_path)
    
    # Also delete myself
    self_path = os.path.join(base_path, "execute_cleanup.py")
    print("Cleanup complete!")

if __name__ == "__main__":
    execute()
