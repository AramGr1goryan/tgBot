
const https = require("https");
const req = https.request("https://robixlab.s20.online/v2api/auth/login", {
  method: "POST", headers: {"Content-Type": "application/json"}
}, (res) => {
  let data = "";
  res.on("data", d => data += d);
  res.on("end", () => {
    const token = JSON.parse(data).token;
    
    // Try Branch 2
    const req2 = https.request("https://robixlab.s20.online/v2api/2/customer/index", {
      method: "POST", headers: {"X-ALFACRM-TOKEN": token, "Content-Type": "application/json"}
    }, (res2) => {
      let data2 = "";
      res2.on("data", d => data2 += d);
      res2.on("end", () => {
        console.log("Branch 2:", JSON.parse(data2));
        
        // Try Branch 5
        const req3 = https.request("https://robixlab.s20.online/v2api/5/customer/index", {
          method: "POST", headers: {"X-ALFACRM-TOKEN": token, "Content-Type": "application/json"}
        }, (res3) => {
          let data3 = "";
          res3.on("data", d => data3 += d);
          res3.on("end", () => {
            console.log("Branch 5:", JSON.parse(data3));
          });
        });
        req3.write(JSON.stringify({"id": 3402}));
        req3.end();
      });
    });
    req2.write(JSON.stringify({"id": 3402}));
    req2.end();
  });
});
req.write(JSON.stringify({email: "aramgrigoryan2k4@gmail.com", api_key: "70cc373b-bed2-11f0-bfab-3cecefbdd1ae"}));
req.end();

