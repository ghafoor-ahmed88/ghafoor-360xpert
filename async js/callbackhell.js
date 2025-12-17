// Step 1: user login (fake)
function login(user, callback) {
  setTimeout(() => {
    console.log(user + " logged in");
    callback(user); // next step ko call
  }, 1000);
}

// Step 2: fetch profile (fake)
function getProfile(user, callback) {
  setTimeout(() => {
    console.log("Profile fetched for " + user);
    callback({ name: user, age: 25 });
  }, 1000);
}

// Run the flow
login("Ali", function(user){
  getProfile(user, function(profile){
    console.log("Final profile:", profile);
  });
});
