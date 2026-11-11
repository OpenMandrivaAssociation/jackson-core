Name:		jackson-core
Version:	2.23.0
Release:	2
Summary:	Core streaming API for Jackson
Group:		Development/Java
License:	ASL 2.0
URL:		https://github.com/FasterXML/jackson-core
Source0:	https://github.com/FasterXML/jackson-core/archive/refs/tags/jackson-core-%{version}.tar.gz#/jackson-core-%{version}.tar.gz
# Gradle 9.9.1 strictly pins 2.22.3. No prebuilt jars.
Source1:	https://github.com/FasterXML/jackson-core/archive/refs/tags/jackson-core-2.22.3.tar.gz#/jackson-core-2.22.3.tar.gz

BuildArch:	noarch
BuildRequires:	mvn(com.fasterxml.jackson:jackson-base:pom::)
BuildRequires:	mvn(com.fasterxml.jackson:jackson-bom:pom::)
BuildRequires:	mvn(com.fasterxml.jackson:jackson-parent:pom::)
BuildRequires:	mvn(com.fasterxml:oss-parent:pom::)
# oss-parent pins the compiler plugin to this ASM jar.
BuildRequires:	mvn(org.ow2.asm:asm)
BuildRequires:	mvn(ch.randelshofer:fastdoubleparser)
BuildRequires:	jackson-bom >= 2.23.0
BuildRequires:	jackson-parent >= 2.23
BuildRequires:	fasterxml-oss-parent >= 81
BuildRequires:	fastdoubleparser >= 2.0.1
# Literal, so the first rpmbuild -bs records them before sysjar is installed.
BuildRequires:	maven
BuildRequires:	java-current-devel
BuildSystem:	maven

Provides:	jackson2-core = %{version}-%{release}
Obsoletes:	jackson2-core < %{version}-%{release}
Obsoletes:	%{name}-javadoc < %{version}

%description
Streaming parser and generator used by Jackson, with the JSON
implementation of that API. 2.23.0 rejects invalid UTF-8 in
string values, enforces maxStringLength when decoding binary,
stops reads past the end of a byte array, and makes number
accessors independent of call order. Doubles, floats and big
numbers are parsed
with the system fastdoubleparser jar. The bundle plugin is not
packaged, so the jar has no OSGi manifest. Tests are skipped.
2.23.0 stays the default jar. Gradle 9.9.1 strictly pins 2.22.3,
so that jar is installed beside it.

%prep
%setup -q -n jackson-core-jackson-core-%{version}
%setup -q -T -D -a 1 -n jackson-core-jackson-core-%{version}
find . \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -delete
# Shade would vendor fastdoubleparser. Replacer, moditect and the
# bundle plugin are not packaged. jackson-base still points the jar
# plugin at target/classes/META-INF/MANIFEST.MF. A child override does
# not replace that parent pluginManagement entry, so the file has to
# exist. It is the multi-release manifest.
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
(meta / "MANIFEST.MF").write_text(
    "Manifest-Version: 1.0\nMulti-Release: true\n",
    encoding="utf-8",
)
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

# 2.22.3 side jar. fastdoubleparser is class version 52, so --release 8 can load it.
mkdir -p jc222/gen/com/fasterxml/jackson/core/json jc222/classes
sed -e 's/@package@/com.fasterxml.jackson.core.json/' \
	-e 's/@projectversion@/2.22.3/' \
	-e 's/@projectgroupid@/com.fasterxml.jackson.core/' \
	-e 's/@projectartifactid@/jackson-core/' \
	jackson-core-jackson-core-2.22.3/src/main/java/com/fasterxml/jackson/core/json/PackageVersion.java.in \
	> jc222/gen/com/fasterxml/jackson/core/json/PackageVersion.java
grep -F -q 'parseVersion(' jc222/gen/com/fasterxml/jackson/core/json/PackageVersion.java
grep -F -q '"2.22.3"' jc222/gen/com/fasterxml/jackson/core/json/PackageVersion.java
find jackson-core-jackson-core-2.22.3/src/main/java -name '*.java' > jc222/sources.list
test "$(wc -l < jc222/sources.list)" -eq 135
echo jc222/gen/com/fasterxml/jackson/core/json/PackageVersion.java >> jc222/sources.list
javac --release 8 -encoding UTF-8 -Xlint:-options \
	-cp %{_javadir}/fastdoubleparser.jar \
	-d jc222/classes @jc222/sources.list
/bin/cp -a jackson-core-jackson-core-2.22.3/src/main/resources/META-INF jc222/classes/
cat > jc222/manifest.mf << 'EOF'
Manifest-Version: 1.0
Automatic-Module-Name: com.fasterxml.jackson.core

EOF
jar cfm jc222/jackson-core.jar jc222/manifest.mf -C jc222/classes .
jar i jc222/jackson-core.jar
javap -verbose -cp jc222/jackson-core.jar com.fasterxml.jackson.core.JsonFactory | grep -F 'major version: 52'
jar --describe-module -f jc222/jackson-core.jar > jc222/describe.txt
cat jc222/describe.txt
if grep -F -q 'Unable to derive' jc222/describe.txt; then
	exit 1
fi
grep -F -q 'com.fasterxml.jackson.core' jc222/describe.txt
cat > jc222/jackson-core.pom << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.fasterxml.jackson.core</groupId>
  <artifactId>jackson-core</artifactId>
  <version>2.22.3</version>
  <name>Jackson-core</name>
  <description>Core Jackson processing abstractions, implementation for JSON</description>
  <licenses>
    <license>
      <name>Apache License, Version 2.0</name>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>ch.randelshofer</groupId>
      <artifactId>fastdoubleparser</artifactId>
      <version>2.0.1</version>
    </dependency>
  </dependencies>
</project>
EOF

%install -p
sysjar install --buildroot %{buildroot} \
	--artifact jc222/jackson-core.pom:jc222/jackson-core.jar \
	--file-name jackson-core-2.22.3 \
	--filelist .mfiles222
# 2.23 owns jackson-core.sysjar. 2.22.3 keeps a second index.
/bin/mv %{buildroot}/usr/share/sysjar/index/com.fasterxml.jackson.core/jackson-core.sysjar \
	%{buildroot}/usr/share/sysjar/index/com.fasterxml.jackson.core/jackson-core-2.22.3.sysjar
sed -i 's|/usr/share/sysjar/index/com.fasterxml.jackson.core/jackson-core\.sysjar|/usr/share/sysjar/index/com.fasterxml.jackson.core/jackson-core-2.22.3.sysjar|' .mfiles222

%install -a
while IFS= read -r line; do
	grep -qxF -- "$line" .mfiles || printf '%s\n' "$line" >> .mfiles
done < .mfiles222

%check -a
cat > JcSmoke.java << 'EOF'
import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonToken;
public class JcSmoke {
	public static void main(String[] args) throws Exception {
		JsonFactory factory = new JsonFactory();
		try (JsonParser parser = factory.createParser("{\"k\":\"gradle\"}")) {
			if (parser.nextToken() != JsonToken.START_OBJECT) {
				throw new RuntimeException("start");
			}
			if (parser.nextToken() != JsonToken.FIELD_NAME || !"k".equals(parser.currentName())) {
				throw new RuntimeException("field");
			}
			if (parser.nextToken() != JsonToken.VALUE_STRING || !"gradle".equals(parser.getText())) {
				throw new RuntimeException(parser.getText());
			}
		}
		System.out.println(args[0] + " " + factory.version() + " gradle");
	}
}
EOF
javac --release 8 -encoding UTF-8 -Xlint:-options \
	-cp %{buildroot}%{_javadir}/jackson-core.jar JcSmoke.java
java -cp "%{buildroot}%{_javadir}/jackson-core.jar:." JcSmoke jc223_ok > check223.log
cat check223.log
grep -F -q 'jc223_ok 2.23.0 gradle' check223.log
javac --release 8 -encoding UTF-8 -Xlint:-options \
	-cp %{buildroot}%{_javadir}/jackson-core-2.22.3.jar JcSmoke.java
java -cp "%{buildroot}%{_javadir}/jackson-core-2.22.3.jar:%{_javadir}/fastdoubleparser.jar:." JcSmoke jc222_ok > check222.log
cat check222.log
grep -F -q 'jc222_ok 2.22.3 gradle' check222.log

%files -f .mfiles
%doc LICENSE README.md SECURITY.md release-notes/VERSION-2.x
