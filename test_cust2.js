
const https = require("https");
const req = https.request("https://robixlab.s20.online/v2api/auth/login", {
  method: "POST", headers: {"Content-Type": "application/json"}
}, (res) => {
  let data = "";
  res.on("data", d => data += d);
  res.on("end", () => {
    const token = JSON.parse(data).token;
    
    // Let us fetch all customers and see if 3402 is there!
    // Since there might be thousands, we can filter by name if we knew it.
    // Or we can just try passing id as string array
    const body = JSON.stringify({"id": ["3402"]});
    const req2 = https.request("https://robixlab.s20.online/v2api/1/customer/index", {
      method: "POST", headers: {"X-ALFACRM-TOKEN": token, "Content-Type": "application/json"}
    }, (res2) => {
      let data2 = "";
      res2.on("data", d => data2 += d);
      res2.on("end", () => {
        console.log("String Array:", JSON.parse(data2));
        
        // Try passing id as int array
        const body3 = JSON.stringify({"id": [3402]});
        const req3 = https.request("https://robixlab.s20.online/v2api/1/customer/index", {
          method: "POST", headers: {"X-ALFACRM-TOKEN": token, "Content-Type": "application/json"}
        }, (res3) => {
          let data3 = "";
          res3.on("data", d => data3 += d);
          res3.on("end", () => {
            console.log("Int Array:", JSON.parse(data3));
          });
        });
        req3.write(body3);
        req3.end();
        
      });
    });
    req2.write(body);
    req2.end();
  });
});
req.write(JSON.stringify({email: "aramgrigoryan2k4@gmail.com", api_key: "70cc373b-bed2-11f0-bfab-3cecefbdd1ae"}));
req.end();

