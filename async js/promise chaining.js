new Promise(resolve => resolve(5))
  .then(result => result * 2)
  .then(result => console.log(result)); // 10
 