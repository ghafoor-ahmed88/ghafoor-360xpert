class User {
  constructor(builder) {
    this.name = builder.name;
    this.email = builder.email;
    this.age = builder.age;
  }
}
class UserBuilder {
  setName(name) {
    this.name = name;
    return this;
  }

  setEmail(email) {
    this.email = email;
    return this;
  }
  setAge(age) {
    this.age = age;
    return this;
  }

  build() {
    return new User(this); // this is the user builder object
  }
}
const user = new UserBuilder()
.setName("Ali")
.setEmail("ali@gmail.com")
.setAge(23)
.build();

console.log(user);
