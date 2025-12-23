import onvif
import os

onvif_dir = os.path.dirname(onvif.__file__)
site_packages = os.path.dirname(onvif_dir)

# Common known paths + the weird one we saw
search_roots = [
    onvif_dir,
    site_packages,
    os.path.abspath(os.path.join(site_packages, '..')),
    os.path.abspath(os.path.join(site_packages, '..', '..')),
    os.path.abspath(os.path.join(site_packages, '..', '..', 'Lib', 'site-packages')), # The likely culprit based on previous find
]

found_path = "NOT_FOUND"

for root in search_roots:
    # Check direct wsdl folder
    candidate = os.path.join(root, 'wsdl')
    if os.path.isfile(os.path.join(candidate, 'devicemgmt.wsdl')):
        found_path = candidate
        break
    
    # Check if wsdl is in a subdirectory
    for r, d, f in os.walk(root):
        if 'devicemgmt.wsdl' in f:
            found_path = r
            break
    if found_path != "NOT_FOUND":
        break

with open('found_path.txt', 'w') as f:
    f.write(found_path)
