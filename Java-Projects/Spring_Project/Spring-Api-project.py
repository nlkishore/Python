import os
import configparser

def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content.strip())

def generate_enterprise_projects():
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.ini')

    # Load Configuration
    config = configparser.ConfigParser()
    if not os.path.exists(config_path):
        print(f"Error: config.ini not found at {config_path}")
        return
    
    config.read(config_path)
    root_val = config['DEFAULT']['root_dir']
    
    # Resolve root_dir relative to the script location if it's not absolute
    if not os.path.isabs(root_val):
        root = os.path.join(script_dir, root_val)
    else:
        root = root_val

    def generate_project_files(base_path, pkg_name, is_jakarta):
        ns = "jakarta" if is_jakarta else "javax"
        pkg_path = pkg_name.replace('.', '/')
        
        # 1. Global Exception Handler
        create_file(f"{base_path}/src/main/java/{pkg_path}/exception/GlobalExceptionHandler.java", f"""
package {pkg_name}.exception;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import java.util.*;

@ControllerAdvice
public class GlobalExceptionHandler {{
    @ExceptionHandler(RuntimeException.class)
    public ResponseEntity<Map<String, Object>> handleRuntime(RuntimeException ex) {{
        Map<String, Object> body = new HashMap<>();
        body.update("timestamp", new Date());
        body.put("message", ex.getMessage());
        return new ResponseEntity<>(body, HttpStatus.INTERNAL_SERVER_ERROR);
    }}
}}""")

        # 2. Product Entity
        create_file(f"{base_path}/src/main/java/{pkg_path}/model/Product.java", f"""
package {pkg_name}.model;
import {ns}.persistence.*;

@Entity
public class Product {{
    @Id
    @GeneratedValue(strategy = GenerationType.{"SEQUENCE" if is_jakarta else "IDENTITY"})
    private Long id;
    private String name;
    // Getters and Setters...
}}""")

        # 3. Product Service
        create_file(f"{base_path}/src/main/java/{pkg_path}/service/ProductService.java", f"""
package {pkg_name}.service;
import {pkg_name}.dto.ProductDTO;
import org.springframework.stereotype.Service;

@Service
public class ProductService {{
    public ProductDTO findById(Long id) {{
        // Business logic here
        return new ProductDTO(id, "Generated Product");
    }}
}}""")

        # 4. Product Controller with Swagger/OpenAPI Annotations
        swagger_anno = "@io.swagger.v3.oas.annotations.Operation" if is_jakarta else "@io.swagger.annotations.ApiOperation"
        create_file(f"{base_path}/src/main/java/{pkg_path}/controller/ProductController.java", f"""
package {pkg_name}.controller;
import {pkg_name}.dto.ProductDTO;
import {pkg_name}.service.ProductService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/products")
public class ProductController {{
    @Autowired private ProductService service;

    {swagger_anno}(summary = "Get product by ID")
    @GetMapping("/{{id}}")
    public ProductDTO getProduct(@PathVariable Long id) {{
        return service.findById(id);
    }}
}}""")

    # Process Spring 4 and Spring 6
    for section in ['SPRING4', 'SPRING6']:
        is_j = (section == 'SPRING6')
        conf = config[section]
        base = os.path.join(root, conf['project_name'])
        generate_project_files(base, conf['package_name'], is_j)

    print(f"Build Successful. Projects located in: {root}")

if __name__ == "__main__":
    generate_enterprise_projects()