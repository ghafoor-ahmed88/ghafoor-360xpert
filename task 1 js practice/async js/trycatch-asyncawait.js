function fetchData() {
  return new Promise((resolve, reject) => {
    let ok = true;
    setTimeout(() => {
      if(ok) resolve("Data mil gaya");
      else reject("Data nahi mila");
    }, 1000);
  });
}

async function getInfo() {
  try {
    let result = await fetchData();
    console.log(result);
  } catch (error) {
    console.log("Error:", error);
  }
}

getInfo();
