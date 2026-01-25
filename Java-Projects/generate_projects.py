import os
import configparser
from pathlib import Path

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

# ---------------------------------------
# Load base folder from config.ini
# ---------------------------------------
# Path of the folder where the script is located 
script_dir = os.path.dirname(os.path.abspath(__file__)) # Build full path to config.ini 
config_path = os.path.join(script_dir, "config.ini")
config = configparser.ConfigParser()

config.read(config_path)

base_folder = config.get("paths", "base_folder", fallback="generated-projects")

print(f"Using base folder: {base_folder}")

# ---------------------------------------
# Project 1: Tomcat 9 (javax JAXB)
# ---------------------------------------
project9 = os.path.join(base_folder, "jaxb-tomcat9")

pom9 = """<project>
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>jaxb-tomcat9</artifactId>
  <version>1.0</version>
  <packaging>war</packaging>

  <dependencies>

    <dependency>
      <groupId>javax.xml.bind</groupId>
      <artifactId>jaxb-api</artifactId>
      <version>2.3.1</version>
    </dependency>

    <dependency>
      <groupId>org.glassfish.jaxb</groupId>
      <artifactId>jaxb-runtime</artifactId>
      <version>2.3.1</version>
    </dependency>

    <dependency>
      <groupId>javax.servlet</groupId>
      <artifactId>javax.servlet-api</artifactId>
      <version>4.0.1</version>
      <scope>provided</scope>
    </dependency>

  </dependencies>
</project>
"""

person9 = """package com.example.model;

import javax.xml.bind.annotation.XmlRootElement;

@XmlRootElement
public class Person {
    public String name;
    public int age;

    public Person() {}
    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }
}
"""

servlet9 = """package com.example.web;

import com.example.model.Person;
import javax.servlet.*;
import javax.servlet.http.*;
import javax.xml.bind.*;

import java.io.IOException;

public class PersonServlet extends HttpServlet {
    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp)
            throws IOException {

        Person p = new Person("Laxmi", 30);

        try {
            JAXBContext ctx = JAXBContext.newInstance(Person.class);
            Marshaller marshaller = ctx.createMarshaller();
            marshaller.setProperty(Marshaller.JAXB_FORMATTED_OUTPUT, true);

            resp.setContentType("application/xml");
            marshaller.marshal(p, resp.getWriter());

        } catch (JAXBException e) {
            throw new IOException(e);
        }
    }
}
"""

webxml9 = """<web-app xmlns="http://xmlns.jcp.org/xml/ns/javaee"
         version="4.0">

    <servlet>
        <servlet-name>person</servlet-name>
        <servlet-class>com.example.web.PersonServlet</servlet-class>
    </servlet>

    <servlet-mapping>
        <servlet-name>person</servlet-name>
        <url-pattern>/person</url-pattern>
    </servlet-mapping>

</web-app>
"""

write(f"{project9}/pom.xml", pom9)
write(f"{project9}/src/main/java/com/example/model/Person.java", person9)
write(f"{project9}/src/main/java/com/example/web/PersonServlet.java", servlet9)
write(f"{project9}/src/main/webapp/WEB-INF/web.xml", webxml9)

# ---------------------------------------
# Project 2: Tomcat 10 (Jakarta JAXB)
# ---------------------------------------
project10 = os.path.join(base_folder, "jaxb-tomcat10")

pom10 = """<project>
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>jaxb-tomcat10</artifactId>
  <version>1.0</version>
  <packaging>war</packaging>

  <dependencies>

    <dependency>
      <groupId>jakarta.xml.bind</groupId>
      <artifactId>jakarta.xml.bind-api</artifactId>
      <version>4.0.0</version>
    </dependency>

    <dependency>
      <groupId>org.glassfish.jaxb</groupId>
      <artifactId>jaxb-runtime</artifactId>
      <version>4.0.4</version>
    </dependency>

    <dependency>
      <groupId>jakarta.servlet</groupId>
      <artifactId>jakarta.servlet-api</artifactId>
      <version>5.0.0</version>
      <scope>provided</scope>
    </dependency>

  </dependencies>
</project>
"""

person10 = """package com.example.model;

import jakarta.xml.bind.annotation.XmlRootElement;

@XmlRootElement
public class Person {
    public String name;
    public int age;

    public Person() {}
    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }
}
"""

servlet10 = """package com.example.web;

import com.example.model.Person;
import jakarta.servlet.*;
import jakarta.servlet.http.*;
import jakarta.xml.bind.*;

import java.io.IOException;

public class PersonServlet extends HttpServlet {
    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp)
            throws IOException {

        Person p = new Person("Laxmi", 30);

        try {
            JAXBContext ctx = JAXBContext.newInstance(Person.class);
            Marshaller marshaller = ctx.createMarshaller();
            marshaller.setProperty(Marshaller.JAXB_FORMATTED_OUTPUT, true);

            resp.setContentType("application/xml");
            marshaller.marshal(p, resp.getWriter());

        } catch (JAXBException e) {
            throw new IOException(e);
        }
    }
}
"""

webxml10 = """<web-app xmlns="https://jakarta.ee/xml/ns/jakartaee"
         version="5.0">

    <servlet>
        <servlet-name>person</servlet-name>
        <servlet-class>com.example.web.PersonServlet</servlet-class>
    </servlet>

    <servlet-mapping>
        <servlet-name>person</servlet-name>
        <url-pattern>/person</url-pattern>
    </servlet-mapping>

</web-app>
"""

write(f"{project10}/pom.xml", pom10)
write(f"{project10}/src/main/java/com/example/model/Person.java", person10)
write(f"{project10}/src/main/java/com/example/web/PersonServlet.java", servlet10)
write(f"{project10}/src/main/webapp/WEB-INF/web.xml", webxml10)

print("Projects generated successfully:")
print(f" - {project9}")
print(f" - {project10}")