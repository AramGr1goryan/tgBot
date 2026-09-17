
const https = require("https");
const req = https.request("https://robixlab.s20.online/v2api/auth/login", {
  method: "POST", headers: {"Content-Type": "application/json"}
}, (res) => {
  let data = "";
  res.on("data", d => data += d);
  res.on("end", () => {
    const token = JSON.parse(data).token;
    
    const req2 = https.request("https://robixlab.s20.online/v2api/1/lesson/index", {
      method: "POST", headers: {"X-ALFACRM-TOKEN": token, "Content-Type": "application/json"}
    }, (res2) => {
      let data2 = "";
      res2.on("data", d => data2 += d);
      res2.on("end", () => {
        let items = JSON.parse(data2).items;
        if(items && items.length > 0) {
           console.log("Full lesson:", JSON.stringify(items[0], null, 2));
           console.log("Customer count details?", items[0].details ? items[0].details.length : "no details");
        }
      });
    });
    // Request lessons for teacher 20 for 15.09 to 16.09 (we know he has lessons here)
    req2.write(JSON.stringify({ "teacher_id": 20, "date_from": "2026-09-15", "date_to": "2026-09-16" }));
    req2.end();
  });
});
req.write(JSON.stringify({email: "aramgrigoryan2k4@gmail.com", api_key: "70cc373b-bed2-11f0-bfab-3cecefbdd1ae"}));
req.end();

