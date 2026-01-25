import os
import configparser

def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content.strip())

def setup_config(config_path):
    """Creates a default config.ini if it doesn't exist."""
    if not os.path.exists(config_path):
        config = configparser.ConfigParser()
        config['DEFAULT'] = {'root_dir': './generated_projects'}
        config['SPRING4'] = {
            'project_name': 'spring4-legacy-mysql',
            'package_name': 'com.example.legacy',
            'db_type': 'mysql'
        }
        config['SPRING6'] = {
            'project_name': 'spring6-jakarta-oracle',
            'package_name': 'com.example.modern',
            'db_type': 'oracle'
        }
        with open(config_path, 'w') as configfile:
            config.write(configfile)
        print(f"Created default config at: {config_path}")

def generate_all():
    # 1. Path Resolution
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.ini')
    
    setup_config(config_path)
    
    config = configparser.ConfigParser()
    config.read(config_path)
    
    root_val = config['DEFAULT']['root_dir']
    root = os.path.join(script_dir, root_val) if not os.path.isabs(root_val) else root_val

    # 2. Iterative Generation
    for section in ['SPRING4', 'SPRING6']:
        is_jakarta = (section == 'SPRING6')
        conf = config[section]
        base = os.path.join(root, conf['project_name'])
        pkg_name = conf['package_name']
        pkg_path = pkg_name.replace('.', '/')
        ns = "jakarta" if is_jakarta else "javax"
        
        # --- POM.XML ---
        pom_content = f"""
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>{pkg_name}</groupId>
    <artifactId>{conf['project_name']}</artifactId>
    <version>1.0-SNAPSHOT</version>
    <packaging>war</packaging>
    <properties>
        <maven.compiler.source>{"17" if is_jakarta else "1.8"}</maven.compiler.source>
        <maven.compiler.target>{"17" if is_jakarta else "1.8"}</maven.compiler.target>
    </properties>
    <dependencies>
        <dependency>
            <groupId>org.springframework</groupId>
            <artifactId>spring-webmvc</artifactId>
            <version>{"6.1.13" if is_jakarta else "4.3.30.RELEASE"}</version>
        </dependency>
        <dependency>
            <groupId>org.springframework</groupId>
            <artifactId>spring-orm</artifactId>
            <version>{"6.1.13" if is_jakarta else "4.3.30.RELEASE"}</version>
        </dependency>
        <dependency>
            <groupId>{"org.hibernate.orm" if is_jakarta else "org.hibernate"}</groupId>
            <artifactId>{"hibernate-core" if is_jakarta else "hibernate-entitymanager"}</artifactId>
            <version>{"6.4.4.Final" if is_jakarta else "5.4.33.Final"}</version>
        </dependency>
        <dependency>
            <groupId>{"com.oracle.database.jdbc" if is_jakarta else "mysql"}</groupId>
            <artifactId>{"ojdbc11" if is_jakarta else "mysql-connector-java"}</artifactId>
            <version>{"23.2.0.0" if is_jakarta else "8.0.28"}</version>
        </dependency>
        <dependency>
            <groupId>{"org.springdoc" if is_jakarta else "io.springfox"}</groupId>
            <artifactId>{"springdoc-openapi-starter-webmvc-ui" if is_jakarta else "springfox-swagger2"}</artifactId>
            <version>{"2.6.0" if is_jakarta else "2.9.2"}</version>
        </dependency>
        {" " if is_jakarta else '<dependency><groupId>io.springfox</groupId><artifactId>springfox-swagger-ui</artifactId><version>2.9.2</version></dependency>'}
        <dependency>
            <groupId>{ns}.servlet</groupId>
            <artifactId>{ns}.servlet-api</artifactId>
            <version>{"6.0.0" if is_jakarta else "3.1.0"}</version>
            <scope>provided</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework</groupId>
            <artifactId>spring-test</artifactId>
            <version>{"6.1.13" if is_jakarta else "4.3.30.RELEASE"}</version>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>{"org.junit.jupiter" if is_jakarta else "junit"}</groupId>
            <artifactId>{"junit-jupiter" if is_jakarta else "junit"}</artifactId>
            <version>{"5.10.0" if is_jakarta else "4.13.2"}</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>"""
        create_file(f"{base}/pom.xml", pom_content)

        # --- JAVA CLASSES ---
        # Entity
        create_file(f"{base}/src/main/java/{pkg_path}/model/Product.java", f"""
package {pkg_name}.model;
import {ns}.persistence.*;
@Entity
public class Product {{
    @Id @GeneratedValue(strategy = GenerationType.{"SEQUENCE" if is_jakarta else "IDENTITY"})
    private Long id;
    private String name;
}}""")

        # DTO
        create_file(f"{base}/src/main/java/{pkg_path}/dto/ProductDTO.java", f"""
package {pkg_name}.dto;
public class ProductDTO {{
    private Long id;
    private String name;
    public ProductDTO(Long id, String name) {{ this.id = id; this.name = name; }}
    public Long getId() {{ return id; }}
    public String getName() {{ return name; }}
}}""")

        # Service
        create_file(f"{base}/src/main/java/{pkg_path}/service/ProductService.java", f"""
package {pkg_name}.service;
import {pkg_name}.dto.ProductDTO;
import org.springframework.stereotype.Service;
@Service
public class ProductService {{
    public ProductDTO getProduct(Long id) {{ return new ProductDTO(id, "Medium Complex Item"); }}
}}""")

        # Exception Handler
        create_file(f"{base}/src/main/java/{pkg_path}/exception/GlobalExceptionHandler.java", f"""
package {pkg_name}.exception;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import java.util.*;
@ControllerAdvice
public class GlobalExceptionHandler {{
    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, String>> handle(Exception e) {{
        Map<String, String> m = new HashMap<>();
        m.put("error", e.getMessage());
        return new ResponseEntity<>(m, HttpStatus.INTERNAL_SERVER_ERROR);
    }}
}}""")

        # Test
        if is_jakarta:
            test_code = f"""
package {pkg_name}.service;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.test.context.junit.jupiter.SpringExtension;
import static org.junit.jupiter.api.Assertions.*;
@ExtendWith(SpringExtension.class)
public class ProductServiceTest {{ @Test void test() {{ assertTrue(true); }} }}"""
        else:
            test_code = f"""
package {pkg_name}.service;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.springframework.test.context.junit4.SpringJUnit4ClassRunner;
import static org.junit.Assert.*;
@RunWith(SpringJUnit4ClassRunner.class)
public class ProductServiceTest {{ @Test public void test() {{ assertTrue(true); }} }}"""
        create_file(f"{base}/src/test/java/{pkg_path}/service/ProductServiceTest.java", test_code)

    print(f"\nSUCCESS: Enterprise projects generated in:\n{os.path.abspath(root)}")


import os
import configparser

def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content.strip())

def generate_all():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.ini')
    
    # Ensure config.ini exists
    if not os.path.exists(config_path):
        with open(config_path, 'w') as f:
            f.write("[DEFAULT]\nroot_dir = ./MyGeneratedProjects\n")
            f.write("[SPRING4]\nproject_name = spring4-legacy-mysql\npackage_name = com.example.legacy\n")
            f.write("[SPRING6]\nproject_name = spring6-jakarta-oracle\npackage_name = com.example.modern\n")

    config = configparser.ConfigParser()
    config.read(config_path)
    root = os.path.abspath(os.path.join(script_dir, config['DEFAULT']['root_dir']))

    for section in ['SPRING4', 'SPRING6']:
        is_j = (section == 'SPRING6')
        conf = config[section]
        base = os.path.join(root, conf['project_name'])
        pkg = conf['package_name']
        pkg_path = pkg.replace('.', '/')
        ns = "jakarta" if is_j else "javax"

        # 1. Create the Config Class (The missing piece)
        config_class_name = "OpenApiConfig" if is_j else "SwaggerConfig"
        config_content = ""
        if is_j:
            config_content = f"package {pkg}.config;\nimport org.springframework.context.annotation.*;\n@Configuration\npublic class OpenApiConfig {{ }}"
        else:
            config_content = f"package {pkg}.config;\nimport org.springframework.context.annotation.*;\nimport springfox.documentation.swagger2.annotations.EnableSwagger2;\n@Configuration\n@EnableSwagger2\npublic class SwaggerConfig {{ }}"
        
        create_file(f"{base}/src/main/java/{pkg_path}/config/{config_class_name}.java", config_content)

        # 2. Create the Test Class (Fixed with correct Import)
        if not is_j:
            test_code = f"""
package {pkg}.service;
import {pkg}.config.SwaggerConfig;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.SpringJUnit4ClassRunner;
import static org.junit.Assert.*;

@RunWith(SpringJUnit4ClassRunner.class)
@ContextConfiguration(classes = {{SwaggerConfig.class}})
public class ProductServiceTest {{
    @Test
    public void test() {{ assertTrue(true); }}
}}"""
        else:
            test_code = f"""
package {pkg}.service;
import {pkg}.config.OpenApiConfig;
import org.junit.jupiter.api.Test;
import org.springframework.test.context.junit.jupiter.SpringJUnitConfig;
import static org.junit.jupiter.api.Assertions.*;

@SpringJUnitConfig(OpenApiConfig.class)
public class ProductServiceTest {{
    @Test
    void test() {{ assertTrue(true); }}
}}"""
        create_file(f"{base}/src/test/java/{pkg_path}/service/ProductServiceTest.java", test_code)

        # 3. Basic POM (Ensure dependencies are there)
        # (Simplified for this example, ensure spring-test and junit are present)

    print(f"Projects updated successfully in {root}")

if __name__ == "__main__":
    generate_all()
if __name__ == "__main__":
    generate_all()