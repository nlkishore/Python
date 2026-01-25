import os

def add_swagger_configs():
    # Spring 4 Swagger 2 Config
    s4_path = "spring4-jpa-mysql/src/main/java/com/example/config/SwaggerConfig.java"
    os.makedirs(os.path.dirname(s4_path), exist_ok=True)
    with open(s4_path, "w") as f:
        f.write("""package com.example.config;
import org.springframework.context.annotation.*;
import org.springframework.web.servlet.config.annotation.*;
import springfox.documentation.builders.*;
import springfox.documentation.spi.DocumentationType;
import springfox.documentation.spring.web.plugins.Docket;
import springfox.documentation.swagger2.annotations.EnableSwagger2;

@Configuration
@EnableSwagger2
@EnableWebMvc
public class SwaggerConfig extends WebMvcConfigurerAdapter {
    @Bean
    public Docket api() {
        return new Docket(DocumentationType.SWAGGER_2).select()
            .apis(RequestHandlerSelectors.any()).paths(PathSelectors.any()).build();
    }
    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        registry.addResourceHandler("swagger-ui.html").addResourceLocations("classpath:/META-INF/resources/");
        registry.addResourceHandler("/webjars/**").addResourceLocations("classpath:/META-INF/resources/webjars/");
    }
}""")

    # Spring 6 OpenAPI 3 Config
    s6_path = "spring6-jpa-oracle/src/main/java/com/example/config/OpenApiConfig.java"
    os.makedirs(os.path.dirname(s6_path), exist_ok=True)
    with open(s6_path, "w") as f:
        f.write("""package com.example.config;
import io.swagger.v3.oas.models.*;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.*;
import org.springframework.web.servlet.config.annotation.EnableWebMvc;

@Configuration
@EnableWebMvc
public class OpenApiConfig {
    @Bean
    public OpenAPI apiInfo() {
        return new OpenAPI().info(new Info().title("Jakarta API").version("1.0"));
    }
}""")
    print("Swagger and OpenAPI configurations added to projects.")

if __name__ == "__main__":
    add_swagger_configs()