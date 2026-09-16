
const https = require("https");
const req = https.request("https://robixlab.s20.online/v2api/auth/login", {
  method: "POST", headers: {"Content-Type": "application/json"}
}, (res) => {
  let data = "";
  res.on("data", d => data += d);
  res.on("end", () => {
    const token = JSON.parse(data).token;
    
    // Accounts
    const req2 = https.request("https://robixlab.s20.online/v2api/1/pay-account/index", {
      method: "POST", headers: {"X-ALFACRM-TOKEN": token, "Content-Type": "application/json"}
    }, (res2) => {
      let data2 = "";
      res2.on("data", d => data2 += d);
      res2.on("end", () => {
        console.log("Accounts:");
        JSON.parse(data2).items.forEach(i => console.log(i.id, i.name));
        
        // Items
        const req3 = https.request("https://robixlab.s20.online/v2api/1/pay-item/index", {
          method: "POST", headers: {"X-ALFACRM-TOKEN": token, "Content-Type": "application/json"}
        }, (res3) => {
          let data3 = "";
          res3.on("data", d => data3 += d);
          res3.on("end", () => {
            console.log("\nItems:");
            JSON.parse(data3).items.forEach(i => console.log(i.id, i.name));
          });
        });
        req3.write(JSON.stringify({category: 1}));
        req3.end();
      });
    });
    req2.write("{}");
    req2.end();
  });
});
req.write(JSON.stringify({email: "aramgrigoryan2k4@gmail.com", api_key: "70cc373b-bed2-11f0-bfab-3cecefbdd1ae"}));
req.end();

