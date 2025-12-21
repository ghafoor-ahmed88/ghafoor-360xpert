class Employee {
  constructor(name) {
    this.name = name;
  }

  show() {
    console.log("Employee:", this.name);
  }
}
class Team {
  constructor(name) {
    this.name = name;
    this.members = [];
  }

  add(member) {
    this.members.push(member);
  }

  show() {
    console.log("Team:", this.name);
    this.members.forEach(member => member.show());
  }
}
const emp1 = new Employee("Ali");
const emp2 = new Employee("Ahmed");
const emp3 = new Employee("Ahmed");

const team = new Team("Developers");
team.add(emp1);
team.add(emp2);
team.add(emp3);

team.show();
