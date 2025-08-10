import xml.etree.ElementTree as ET

rewrite_namespaces = [
    "urn:jboss:domain:security",
    "urn:jboss:domain:web",
    "urn:jboss:domain:jacorb",
    "urn:jboss:domain:messaging",
    "urn:jboss:domain:cmp",
    "urn:jboss:domain:jbossws"
]

tree = ET.parse("standalone-ha.xml")
root = tree.getroot()
profile = root.find('profile')

print("Subsystems requiring rewrite for JBoss 8:")
for subsystem in profile.findall('subsystem'):
    ns = subsystem.tag
    for rewrite_ns in rewrite_namespaces:
        if rewrite_ns in ns:
            print(f" - {ns}")