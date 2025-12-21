class database {
    constructor() {
        if (database.instance) {
           return database.instance;
        }
        this.connection = "Database connection OBJ 1";
        database.instance = this;
        console.log("Database connection established")
    }
}

const db1 = new database();
const db2 = new database();

console.log(db1 === db2); // true


