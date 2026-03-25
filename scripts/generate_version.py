import json
import os
import sys
import subprocess
import re

def get_git_version():
    """Retrieve version from git tags if available."""
    try:
        # Get something like "0.9.0-4-g201a444" or "0.9.0" or "0.9.0-dirty"
        cmd = ["git", "describe", "--tags", "--always", "--dirty"]
        version = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8").strip()
        
        # Remove leading 'v' if present
        if version.startswith('v'):
            version = version[1:]
        return version
    except Exception:
        return None

def parse_numeric_version(version_str):
    """Extract (Major, Minor, Patch, Build) from a version string."""
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", version_str)
    if match:
        major, minor, patch = map(int, match.groups())
        build = 0
        
        # Extract build number from git describe pattern (e.g., -4-g...)
        build_match = re.search(r"-(\d+)-", version_str)
        if build_match:
            build = int(build_match.group(1))
            
        return (major, minor, patch, build)
    return (0, 0, 0, 0)

def generate_version_files():
    # Paths
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    version_json_path = os.path.join(project_root, 'versioninfo.json')
    src_version_path = os.path.join(project_root, 'src', '__version__.py')
    build_dir = os.path.join(project_root, 'build')
    build_version_info_path = os.path.join(build_dir, 'version_info.txt')
    build_args_path = os.path.join(build_dir, 'pyinstaller_args.txt')

    # Ensure build dir exists
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)

    # Read versioninfo.json for fallback info and strings
    try:
        with open(version_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {version_json_path} not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse {version_json_path}: {e}")
        sys.exit(1)

    # Extract base info
    string_info = data.get('StringFileInfo', {})
    company = string_info.get('CompanyName', '')
    copyright_str = string_info.get('LegalCopyright', '')
    product_name = string_info.get('ProductName', 'pyCol')
    description = string_info.get('FileDescription', '')
    
    # Try Git first, fallback to JSON
    git_ver = get_git_version()
    if git_ver:
        version_str = git_ver
        file_version_tuple = parse_numeric_version(git_ver)
        product_version_tuple = file_version_tuple
        print(f"Using Git version: {version_str} {file_version_tuple}")
    else:
        version_str = string_info.get('ProductVersion', '0.0.0')
        fixed_info = data.get('FixedFileInfo', {})
        file_version_tuple = (
            fixed_info.get('FileVersion', {}).get('Major', 0),
            fixed_info.get('FileVersion', {}).get('Minor', 0),
            fixed_info.get('FileVersion', {}).get('Patch', 0),
            fixed_info.get('FileVersion', {}).get('Build', 0)
        )
        product_version_tuple = (
            fixed_info.get('ProductVersion', {}).get('Major', 0),
            fixed_info.get('ProductVersion', {}).get('Minor', 0),
            fixed_info.get('ProductVersion', {}).get('Patch', 0),
            fixed_info.get('ProductVersion', {}).get('Build', 0)
        )
        print(f"Using fallback JSON version: {version_str}")

    # Extract enabled plugins for runtime info
    plugins_dict = data.get('Plugins', {})
    enabled_plugins = [k for k, v in plugins_dict.items() if v]

    # 1. Generate src/__version__.py
    print(f"Generating {src_version_path}...")
    with open(src_version_path, 'w', encoding='utf-8') as f:
        f.write("# Auto-generated from versioninfo.json/Git - DO NOT EDIT\n")
        f.write(f'__version__ = "{version_str}"\n')
        f.write(f'__app_name__ = "{product_name}"\n')
        f.write(f'__description__ = "{description}"\n')
        f.write(f'__company__ = "{company}"\n')
        f.write(f'__copyright__ = "{copyright_str}"\n')
        f.write(f'__plugins__ = {enabled_plugins!r}\n')

    # 2. Generate build/version_info.txt (PyInstaller syntax)
    print(f"Generating {build_version_info_path}...")
    
    # Python-representation for PyInstaller
    # We construct the VSVersionInfo object string manually/safely
    
    version_info_content = f"""
# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    filevers={file_version_tuple},
    prodvers={product_version_tuple},
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to define OS for Windows 95/98.
    # 0x40000 - 32-bit Windows.
    OS=0x40004,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', '{company}'),
        StringStruct('FileDescription', '{string_info.get("FileDescription", "")}'),
        StringStruct('FileVersion', '{string_info.get("FileVersion", "")}'),
        StringStruct('InternalName', '{string_info.get("InternalName", "")}'),
        StringStruct('LegalCopyright', '{copyright_str}'),
        StringStruct('OriginalFilename', '{string_info.get("OriginalFilename", "")}'),
        StringStruct('ProductName', '{product_name}'),
        StringStruct('ProductVersion', '{version_str}')])
      ]), 
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    with open(build_version_info_path, 'w', encoding='utf-8') as f:
        f.write(version_info_content)

    # 3. Generate build/pyinstaller_args.txt (Plugin flags)
    print(f"Generating {build_args_path}...")
    plugins = data.get('Plugins', {})
    args = []
    
    for plugin_name, enabled in plugins.items():
        if enabled:
            # Source: src/plugins/{name}
            # Dest: plugins/{name}
            # Separator for --add-data is ';' on Windows and ':' on Linux
            sep = os.pathsep
            args.append(f'--add-data "src/plugins/{plugin_name}{sep}plugins/{plugin_name}"')
            print(f"  [+] Enabling plugin: {plugin_name}")
        else:
            print(f"  [-] Skipping plugin: {plugin_name}")
            
    with open(build_args_path, 'w', encoding='utf-8') as f:
        f.write(" ".join(args))

    print("Done.")

if __name__ == "__main__":
    generate_version_files()
