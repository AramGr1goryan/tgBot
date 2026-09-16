
const https = require("https");
const req = https.request("https://robixlab.s20.online/v2api/auth/login", {
  method: "POST", headers: {"Content-Type": "application/json"}
}, (res) => {
  let data = "";
  res.on("data", d => data += d);
  res.on("end", () => {
    const token = JSON.parse(data).token;
    
    // According to AlfaCRM API, filter array values should be passed correctly. 
    // Sometimes it requires {"id": 3402} or {"id": [3402]} 
    // Or maybe we can fetch all customers at once using page 0 and limit 1? 
    // No, we need exactly these IDs!
    const body = JSON.stringify({"id": 3402});
    const req2 = https.request("https://robixlab.s20.online/v2api/1/customer/index", {
      method: "POST", headers: {"X-ALFACRM-TOKEN": token, "Content-Type": "application/json"}
    }, (res2) => {
      let data2 = "";
      res2.on("data", d => data2 += d);
      res2.on("end", () => {
        console.log(JSON.parse(data2));
      });
    });
    req2.write(body);
    req2.end();
  });
});
req.write(JSON.stringify({email: "aramgrigoryan2k4@gmail.com", api_key: "70cc373b-bed2-11f0-bfab-3cecefbdd1ae"}));
req.end();

