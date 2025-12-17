function greet(result) {
  console.log("Hello, sum is " + result);
}

function add(a, b, callback) {
  let sum = a + b;
  callback(sum);  // yahi callback chal raha hai
}

add(1, 2, greet);
