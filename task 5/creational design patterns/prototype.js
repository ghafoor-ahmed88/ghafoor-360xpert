// existing Prototype object 
const userPrototype = {
  name: "Default User",
  role: "user",
  

  clone() {
    // making controlled clone 
    return {
      name: this.name,
      role: this.role
    };
  }
};

// Clone 1
const user1 = userPrototype.clone();
user1.name = "Ali";

// Clone 2
const user2 = userPrototype.clone();
user2.name = "Sara";


console.log(user1); // { name: 'Ali', role: 'user' }
console.log(user2); // { name: 'Sara', role: 'user' }
