import json
import subprocess
import re
from pathlib import Path


def get_git_version():
    """Retrieve version from git tags if available."""
    try:
        cmd = ["git", "describe", "--tags", "--always"]
        version = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8").strip()
        if version.startswith('v'):
            version = version[1:]
        # Extract base version (X.Y.Z) for the installer filename
        match = re.search(r"(\d+\.\d+\.\d+)", version)
        return match.group(1) if match else version
    except Exception:
        return None


def main():
    project_root = Path(__file__).parent.parent
    
    # Load fallback info from JSON
    with open(project_root / 'versioninfo.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Try Git version first, then fallback
    git_ver = get_git_version()
    if git_ver:
        version = git_ver
        print(f"Using Git version for ISS: {version}")
    else:
        fixed = data['FixedFileInfo']['ProductVersion']
        version = f"{fixed['Major']}.{fixed['Minor']}.{fixed['Patch']}"
        print(f"Fallback to JSON version for ISS: {version}")
    
    string_info = data['StringFileInfo']
    
    # Read template
    iss_path = project_root / 'scripts' / 'pyCol.iss'
    with open(iss_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace version defines
    import re
    content = re.sub(r'#define MyAppVersion ".*"', f'#define MyAppVersion "{version}"', content)
    content = re.sub(r'#define MyAppPublisher ".*"', f'#define MyAppPublisher "{string_info.get("CompanyName", "DIYAstro")}"', content)
    content = re.sub(r'OutputBaseFilename=pyCol_Setup_.*', f'OutputBaseFilename=pyCol_Setup_{version}', content)
    
    # Update VersionInfo directives for installer EXE properties
    copyright_text = string_info.get('LegalCopyright', 'GNU General Public License v3.0')
    content = re.sub(r'VersionInfoCopyright=.*', f'VersionInfoCopyright={copyright_text}', content)
    
    # Write back
    with open(iss_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Updated pyCol.iss with version {version}")


if __name__ == '__main__':
    main()
