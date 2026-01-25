package com.example.model;

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
