function wait1sec() {
  return new Promise(resolve => {
    setTimeout(() => resolve("1 second done"), 1000);
  });
}

async function wait() {
  console.log("Waiting 1 second...");
  let msg = await wait1sec();
  console.log(msg);
}

wait();
