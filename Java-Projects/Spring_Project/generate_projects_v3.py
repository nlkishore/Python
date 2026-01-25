import os
import configparser
import shutil

def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content.strip())

def generate_spring4_final_fix():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.ini')
    
    config = configparser.ConfigParser()
    config.read(config_path)
    
    conf = config['SPRING4']
    root_dir = os.path.abspath(os.path.join(script_dir, config['DEFAULT']['root_dir']))
    base = os.path.join(root_dir, conf['project_name'])
    pkg = conf['package_name']
    pkg_path = pkg.replace('.', '/')

    if os.path.exists(base):
        shutil.rmtree(base)

    # 1. POM.XML - Added CGLIB and fixed versions for JDK 8/11/17 compatibility
    pom_content = f"""
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>{pkg}</groupId>
    <artifactId>{conf['project_name']}</artifactId>
    <version>1.0-SNAPSHOT</version>
    <packaging>war</packaging>
    <properties>
        <maven.compiler.source>1.8</maven.compiler.source>
        <maven.compiler.target>1.8</maven.compiler.target>
        <spring.version>4.3.30.RELEASE</spring.version>
    </properties>
    <dependencies>
        <dependency>
            <groupId>org.springframework</groupId>
            <artifactId>spring-context</artifactId>
            <version>${{spring.version}}</version>
        </dependency>
        <dependency>
            <groupId>org.springframework</groupId>
            <artifactId>spring-webmvc</artifactId>
            <version>${{spring.version}}</version>
        </dependency>
        <dependency>
            <groupId>cglib</groupId>
            <artifactId>cglib-nodep</artifactId>
            <version>3.3.0</version>
        </dependency>
        <dependency>
            <groupId>javax.servlet</groupId>
            <artifactId>javax.servlet-api</artifactId>
            <version>3.1.0</version>
            <scope>provided</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework</groupId>
            <artifactId>spring-test</artifactId>
            <version>${{spring.version}}</version>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>junit</groupId>
            <artifactId>junit</artifactId>
            <version>4.13.2</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>"""
    create_file(f"{base}/pom.xml", pom_content)

    # 2. APP CONFIG - Removed @EnableWebMvc for the Test context to avoid proxy issues
    config_content = f"""
package {pkg}.config;
import org.springframework.context.annotation.*;

@Configuration
@ComponentScan(basePackages = "{pkg}")
public class AppConfig {{
    // Lite config for testing
}}"""
    create_file(f"{base}/src/main/java/{pkg_path}/config/AppConfig.java", config_content)

    # 3. SERVICE
    create_file(f"{base}/src/main/java/{pkg_path}/service/ProductService.java", f"""
package {pkg}.service;
import org.springframework.stereotype.Service;
@Service
public class ProductService {{
    public String status() {{ return "OK"; }}
}}""")

    # 4. TEST CLASS - Uses the Lite Config
    test_code = f"""
package {pkg}.service;
import {pkg}.config.AppConfig;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.SpringJUnit4ClassRunner;
import static org.junit.Assert.*;

@RunWith(SpringJUnit4ClassRunner.class)
@ContextConfiguration(classes = {{AppConfig.class}})
public class ProductServiceTest {{
    @Autowired
    private ProductService productService;

    @Test
    public void testSimple() {{
        assertNotNull(productService);
        assertEquals("OK", productService.status());
    }}
}}"""
    create_file(f"{base}/src/test/java/{pkg_path}/service/ProductServiceTest.java", test_code)

    print(f"Project generated. Please run 'mvn clean test' in {base}")

if __name__ == "__main__":
    generate_spring4_final_fix()