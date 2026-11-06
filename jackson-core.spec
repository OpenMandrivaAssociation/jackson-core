Name:		jackson-core
Version:	2.21.8
Release:	1
Summary:	Core streaming API for Jackson
Group:		Development/Java
License:	ASL 2.0
URL:		https://github.com/FasterXML/jackson-core
Source0:	https://github.com/FasterXML/jackson-core/archive/refs/tags/jackson-core-%{version}.tar.gz#/jackson-core-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	mvn(com.fasterxml.jackson:jackson-base:pom::)
BuildRequires:	mvn(com.fasterxml.jackson:jackson-bom:pom::)
BuildRequires:	mvn(com.fasterxml.jackson:jackson-parent:pom::)
BuildRequires:	mvn(com.fasterxml:oss-parent:pom::)
# oss-parent pins the compiler plugin to this ASM jar.
BuildRequires:	mvn(org.ow2.asm:asm)
BuildRequires:	mvn(ch.randelshofer:fastdoubleparser)
# Literal, so the first rpmbuild -bs records them before sysjar is installed.
BuildRequires:	maven
BuildRequires:	java-current-devel
BuildSystem:	maven

Provides:	jackson2-core = %{version}-%{release}
Obsoletes:	jackson2-core < %{version}-%{release}
Obsoletes:	%{name}-javadoc < %{version}

%description
Streaming parser and generator used by Jackson, with the JSON
implementation of that API. 2.21.8 fixes escape handling and
non-blocking parsing, including CVE-2026-89407, CVE-2026-89425
and CVE-2026-68498. Doubles, floats and big numbers are parsed
with the system fastdoubleparser jar. The bundle plugin is not
packaged, so the jar has no OSGi manifest. Tests are skipped.

%prep
%setup -q -n jackson-core-jackson-core-%{version}
# Shade would vendor fastdoubleparser. Replacer, moditect and the
# bundle plugin are not packaged. jackson-base still points the jar
# plugin at a manifest those plugins never write.
python - <<'PY'
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "http://maven.apache.org/POM/4.0.0"
ET.register_namespace("", NS)
ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")

def local(tag):
    return tag.rsplit("}", 1)[-1]

def artifact_of(elem):
    for item in elem:
        if local(item.tag) == "artifactId":
            return (item.text or "").strip()
    return ""

drop = {
    "jacoco-maven-plugin",
    "maven-enforcer-plugin",
    "maven-surefire-plugin",
    "replacer",
    "cyclonedx-maven-plugin",
    "moditect-maven-plugin",
    "build-helper-maven-plugin",
    "maven-shade-plugin",
    "gradle-module-metadata-maven-plugin",
    "animal-sniffer-maven-plugin",
    "maven-site-plugin",
}
path = Path("pom.xml")
tree = ET.parse(path)
root = tree.getroot()
removed = []
for parent in root.iter():
    for child in list(parent):
        name = local(child.tag)
        if name in ("repositories", "pluginRepositories"):
            parent.remove(child)
            removed.append(name)
            continue
        if name != "plugin":
            continue
        artifact = artifact_of(child)
        if artifact in drop:
            parent.remove(child)
            removed.append(artifact)
for parent in list(root.iter()):
    if local(parent.tag) != "dependencies":
        continue
    for child in list(parent):
        if local(child.tag) != "dependency":
            continue
        scope = ""
        for item in child:
            if local(item.tag) == "scope":
                scope = (item.text or "").strip()
        if scope == "test":
            parent.remove(child)
            removed.append("dep:" + artifact_of(child))
missing = drop - set(removed)
if missing:
    raise SystemExit("not removed " + " ".join(sorted(missing)))

jar = None
for parent in root.iter():
    for child in parent:
        if local(child.tag) == "plugin" and artifact_of(child) == "maven-jar-plugin":
            jar = child
if jar is None:
    raise SystemExit("jar plugin missing")
for item in list(jar):
    if local(item.tag) == "configuration":
        jar.remove(item)
tag = "{" + NS + "}"
conf = ET.Element(tag + "configuration")
conf.set("combine.self", "override")
archive = ET.SubElement(conf, tag + "archive")
entries = ET.SubElement(archive, tag + "manifestEntries")
flag = ET.SubElement(entries, tag + "Multi-Release")
flag.text = "true"
jar.append(conf)
tree.write(path, encoding="UTF-8", xml_declaration=True)
text = path.read_text(encoding="utf-8")
if "maven-shade-plugin" in text or "manifestFile" in text:
    raise SystemExit("shade or manifestFile survived")
if "fastdoubleparser" not in text:
    raise SystemExit("fastdoubleparser dependency missing")

src = Path("src/main/java/com/fasterxml/jackson/core/json/PackageVersion.java.in")
body = src.read_text(encoding="utf-8")
body = body.replace("@package@", "com.fasterxml.jackson.core.json")
body = body.replace("@projectversion@", "%{version}")
body = body.replace("@projectgroupid@", "com.fasterxml.jackson.core")
body = body.replace("@projectartifactid@", "jackson-core")
for token in ("@package@", "@projectversion@", "@projectgroupid@", "@projectartifactid@"):
    if token in body:
        raise SystemExit("placeholder left")
src.with_suffix("").write_text(body, encoding="utf-8")
src.unlink()
license_file = Path("LICENSE")
if not license_file.is_file():
    raise SystemExit("LICENSE missing")
meta = Path("src/main/resources/META-INF")
meta.mkdir(parents=True, exist_ok=True)
(meta / "LICENSE").write_bytes(license_file.read_bytes())
PY

%build -a
mkdir -p target/classes/META-INF/versions/9
javac --release 9 \
	--patch-module com.fasterxml.jackson.core=target/classes \
	-d target/classes/META-INF/versions/9 \
	src/moditect/module-info.java
test -s target/classes/META-INF/versions/9/module-info.class
jar uf target/jackson-core-%{version}.jar -C target/classes META-INF/versions/9/module-info.class
jar tf target/jackson-core-%{version}.jar | grep -q '^META-INF/versions/9/module-info.class$'

%files -f .mfiles
%doc LICENSE README.md SECURITY.md release-notes/VERSION-2.x
