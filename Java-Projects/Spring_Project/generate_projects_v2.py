import os
import configparser
import shutil

def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content.strip())

def generate_spring4_clean_build():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.ini')
    
    config = configparser.ConfigParser()
    config.read(config_path)
    
    # Target Spring 4 section
    conf = config['SPRING4']
    root_dir = os.path.abspath(os.path.join(script_dir, config['DEFAULT']['root_dir']))
    base = os.path.join(root_dir, conf['project_name'])
    pkg = conf['package_name']
    pkg_path = pkg.replace('.', '/')

    # 1. HARD CLEANUP
    if os.path.exists(base):
        print(f"Cleaning project folder: {base}")
        shutil.rmtree(base)

    # 2. POM.XML with fixed Swagger/Spring compatibility
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
            <artifactId>spring-webmvc</artifactId>
            <version>${{spring.version}}</version>
        </dependency>
        <dependency>
            <groupId>org.springframework</groupId>
            <artifactId>spring-orm</artifactId>
            <version>${{spring.version}}</version>
        </dependency>
        <dependency>
            <groupId>javax.servlet</groupId>
            <artifactId>javax.servlet-api</artifactId>
            <version>3.1.0</version>
            <scope>provided</scope>
        </dependency>
        <dependency>
            <groupId>io.springfox</groupId>
            <artifactId>springfox-swagger2</artifactId>
            <version>2.9.2</version>
        </dependency>
        <dependency>
            <groupId>io.springfox</groupId>
            <artifactId>springfox-swagger-ui</artifactId>
            <version>2.9.2</version>
        </dependency>
        <dependency>
            <groupId>com.fasterxml.jackson.core</groupId>
            <artifactId>jackson-databind</artifactId>
            <version>2.9.10.8</version>
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

    # 3. APP CONFIG (Proper Scanning)
    config_content = f"""
package {pkg}.config;
import org.springframework.context.annotation.*;
import org.springframework.web.servlet.config.annotation.EnableWebMvc;
import springfox.documentation.swagger2.annotations.EnableSwagger2;
import springfox.documentation.spring.web.plugins.Docket;
import springfox.documentation.spi.DocumentationType;
import springfox.documentation.builders.PathSelectors;
import springfox.documentation.builders.RequestHandlerSelectors;

@Configuration
@EnableWebMvc
@EnableSwagger2
@ComponentScan(basePackages = "{pkg}")
public class AppConfig {{
    @Bean
    public Docket api() {{ 
        return new Docket(DocumentationType.SWAGGER_2)
            .select()                                  
            .apis(RequestHandlerSelectors.any())
            .paths(PathSelectors.any())                          
            .build();                                           
    }}
}}"""
    create_file(f"{base}/src/main/java/{pkg_path}/config/AppConfig.java", config_content)

    # 4. PRODUCT SERVICE
    create_file(f"{base}/src/main/java/{pkg_path}/service/ProductService.java", f"""
package {pkg}.service;
import org.springframework.stereotype.Service;
@Service
public class ProductService {{
    public String getTest() {{ return "Success"; }}
}}""")

    # 5. TEST CLASS (Correctly Mocked for Web)
    test_code = f"""
package {pkg}.service;
import {pkg}.config.AppConfig;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.SpringJUnit4ClassRunner;
import org.springframework.test.context.web.WebAppConfiguration;
import static org.junit.Assert.*;

@RunWith(SpringJUnit4ClassRunner.class)
@ContextConfiguration(classes = {{AppConfig.class}})
@WebAppConfiguration
public class ProductServiceTest {{
    @Autowired
    private ProductService productService;

    @Test
    public void testContextLoads() {{
        assertNotNull(productService);
        assertEquals("Success", productService.getTest());
    }}
}}"""
    create_file(f"{base}/src/test/java/{pkg_path}/service/ProductServiceTest.java", test_code)

    print(f"\nSUCCESS: Clean Spring 4.x project generated at: {base}")

if __name__ == "__main__":
    generate_spring4_clean_build()