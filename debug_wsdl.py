import onvif
import os

print(f"onvif package file: {onvif.__file__}")
onvif_dir = os.path.dirname(onvif.__file__)
site_packages = os.path.dirname(onvif_dir)

print(f"onvif dir: {onvif_dir}")
print(f"site_packages: {site_packages}")

possible_paths = [
    os.path.join(onvif_dir, 'wsdl'),
    os.path.join(site_packages, 'wsdl'),
    # Try looking for a 'wsdl' folder in the user base if that's what's happening
    os.path.join(os.path.dirname(site_packages), 'wsdl'), # python311/wsdl?
    os.path.join(os.path.dirname(os.path.dirname(site_packages)), 'wsdl'), # Base?
    # Based on find_by_name result:
    os.path.join(os.path.dirname(os.path.dirname(site_packages)), 'Lib', 'site-packages', 'wsdl'),
]

found = False
for p in possible_paths:
    exists = os.path.isdir(p)
    file_exists = os.path.isfile(os.path.join(p, 'devicemgmt.wsdl'))
    print(f"Checking: {p} -> Dir Exists: {exists}, Contains wsdl: {file_exists}")
    if file_exists:
        print(f"FOUND WSDL DIR: {p}")
        found = True

if not found:
    print("Searching recursively in site_packages...")
    for root, dirs, files in os.walk(site_packages):
        if 'devicemgmt.wsdl' in files:
            print(f"FOUND in walk: {root}")
