package com.example.web;

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
