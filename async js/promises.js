let p = new Promise((resolve, reject) => {
  let success = true;
  if(success) resolve("Done");
  else reject("Error");
});

p.then(result => console.log(result))
 .catch(err => console.log(err))
 .finally(() => console.log("Finished"));
