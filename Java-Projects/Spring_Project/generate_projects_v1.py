import os
import configparser
import shutil

def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content.strip())

def generate_full_enterprise_build():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.ini')
    
    # Check for config.ini
    config = configparser.ConfigParser()
    if not os.path.exists(config_path):
        print("Creating default config.ini...")
        config['DEFAULT'] = {'root_dir': './MyGeneratedProjects'}
        config['SPRING4'] = {'project_name': 'spring4-legacy-mysql', 'package_name': 'com.example.legacy'}
        config['SPRING6'] = {'project_name': 'spring6-jakarta-oracle', 'package_name': 'com.example.modern'}
        with open(config_path, 'w') as f: config.write(f)
    
    config.read(config_path)
    root = os.path.abspath(os.path.join(script_dir, config['DEFAULT']['root_dir']))

    # CLEANUP: Prevent duplicate class errors
    if os.path.exists(root):
        shutil.rmtree(root)

    for section in ['SPRING4', 'SPRING6']:
        is_j = (section == 'SPRING6')
        conf = config[section]
        base = os.path.join(root, conf['project_name'])
        pkg = conf['package_name']
        pkg_path = pkg.replace('.', '/')
        ns = "jakarta" if is_j else "javax"
        
        # --- 1. POM.XML GENERATION ---
        s_ver = "6.1.13" if is_j else "4.3.30.RELEASE"
        hib_ver = "6.4.4.Final" if is_j else "5.4.33.Final"
        java_ver = "17" if is_j else "1.8"
        
        pom_content = f"""
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>{pkg}</groupId>
    <artifactId>{conf['project_name']}</artifactId>
    <version>1.0-SNAPSHOT</version>
    <packaging>war</packaging>
    <properties>
        <maven.compiler.source>{java_ver}</maven.compiler.source>
        <maven.compiler.target>{java_ver}</maven.compiler.target>
    </properties>
    <dependencies>
        <dependency>
            <groupId>org.springframework</groupId>
            <artifactId>spring-webmvc</artifactId>
            <version>{s_ver}</version>
        </dependency>
        <dependency>
            <groupId>org.springframework</groupId>
            <artifactId>spring-orm</artifactId>
            <version>{s_ver}</version>
        </dependency>
        <dependency>
            <groupId>{"org.hibernate.orm" if is_j else "org.hibernate"}</groupId>
            <artifactId>{"hibernate-core" if is_j else "hibernate-entitymanager"}</artifactId>
            <version>{hib_ver}</version>
        </dependency>
        <dependency>
            <groupId>{"com.oracle.database.jdbc" if is_j else "mysql"}</groupId>
            <artifactId>{"ojdbc11" if is_j else "mysql-connector-java"}</artifactId>
            <version>{"23.2.0.0" if is_j else "8.0.28"}</version>
        </dependency>
        <dependency>
            <groupId>{ns}.servlet</groupId>
            <artifactId>{ns}.servlet-api</artifactId>
            <version>{"6.0.0" if is_j else "3.1.0"}</version>
            <scope>provided</scope>
        </dependency>
        <dependency>
            <groupId>{"org.springdoc" if is_j else "io.springfox"}</groupId>
            <artifactId>{"springdoc-openapi-starter-webmvc-ui" if is_j else "springfox-swagger2"}</artifactId>
            <version>{"2.6.0" if is_j else "2.9.2"}</version>
        </dependency>
        {" " if is_j else '<dependency><groupId>io.springfox</groupId><artifactId>springfox-swagger-ui</artifactId><version>2.9.2</version></dependency>'}
        <dependency>
            <groupId>org.springframework</groupId>
            <artifactId>spring-test</artifactId>
            <version>{s_ver}</version>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>{"org.junit.jupiter" if is_j else "junit"}</groupId>
            <artifactId>{"junit-jupiter" if is_j else "junit"}</artifactId>
            <version>{"5.10.0" if is_j else "4.13.2"}</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>"""
        create_file(f"{base}/pom.xml", pom_content)

        # --- 2. CONFIG CLASS (AppConfig.java) ---
        config_content = f"""
package {pkg}.config;
import org.springframework.context.annotation.*;
import org.springframework.web.servlet.config.annotation.EnableWebMvc;
{"import springfox.documentation.swagger2.annotations.EnableSwagger2;import springfox.documentation.spring.web.plugins.Docket;import springfox.documentation.spi.DocumentationType;import springfox.documentation.builders.*;" if not is_j else ""}

@Configuration
@EnableWebMvc
@ComponentScan(basePackages = "{pkg}")
{"@EnableSwagger2" if not is_j else ""}
public class AppConfig {{
    {"@Bean public Docket api() { return new Docket(DocumentationType.SWAGGER_2).select().apis(RequestHandlerSelectors.any()).build(); }" if not is_j else ""}
}}"""
        create_file(f"{base}/src/main/java/{pkg_path}/config/AppConfig.java", config_content)

        # --- 3. DTO & SERVICE ---
        create_file(f"{base}/src/main/java/{pkg_path}/dto/ProductDTO.java", f"package {pkg}.dto;\npublic class ProductDTO {{ private Long id; private String name; public ProductDTO(Long id, String name) {{ this.id = id; this.name = name; }} public Long getId() {{ return id; }} public String getName() {{ return name; }} }}")
        create_file(f"{base}/src/main/java/{pkg_path}/service/ProductService.java", f"package {pkg}.service;\nimport {pkg}.dto.ProductDTO;\nimport org.springframework.stereotype.Service;\n@Service\npublic class ProductService {{ public ProductDTO findById(Long id) {{ return new ProductDTO(id, \"Test Product\"); }} }}")

        # --- 4. TEST CLASS ---
        if is_j:
            test_code = f"package {pkg}.service;\nimport {pkg}.config.AppConfig;\nimport org.junit.jupiter.api.Test;\nimport org.springframework.test.context.junit.jupiter.web.SpringJUnitWebConfig;\nimport static org.junit.jupiter.api.Assertions.*;\n@SpringJUnitWebConfig(AppConfig.class)\npublic class ProductServiceTest {{ @Test void test() {{ assertTrue(true); }} }}"
        else:
            test_code = f"package {pkg}.service;\nimport {pkg}.config.AppConfig;\nimport org.junit.Test;\nimport org.junit.runner.RunWith;\nimport org.springframework.test.context.ContextConfiguration;\nimport org.springframework.test.context.junit4.SpringJUnit4ClassRunner;\nimport org.springframework.test.context.web.WebAppConfiguration;\nimport static org.junit.Assert.*;\n@RunWith(SpringJUnit4ClassRunner.class)\n@ContextConfiguration(classes = {{AppConfig.class}})\n@WebAppConfiguration\npublic class ProductServiceTest {{ @Test public void test() {{ assertTrue(true); }} }}"
        create_file(f"{base}/src/test/java/{pkg_path}/service/ProductServiceTest.java", test_code)

    print(f"\nSUCCESS: Enterprise builds (including pom.xml) generated in {root}")

if __name__ == "__main__":
    generate_full_enterprise_build()