#!/usr/bin/env python3
"""
Generate Inno Setup script with version info from versioninfo.json.
"""
import json
from pathlib import Path


def main():
    project_root = Path(__file__).parent.parent
    
    # Load version info
    with open(project_root / 'versioninfo.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    fixed = data['FixedFileInfo']['ProductVersion']
    version = f"{fixed['Major']}.{fixed['Minor']}.{fixed['Patch']}"
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
