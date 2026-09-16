
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
        console.log("Status 1 lessons:", items ? items.length : data2);
      });
    });
    req2.write(JSON.stringify({ "teacher_id": 20, "date_from": "2026-09-17", "date_to": "2026-09-18", "status": 1 }));
    req2.end();
    
    const req3 = https.request("https://robixlab.s20.online/v2api/1/regular-lesson/index", {
      method: "POST", headers: {"X-ALFACRM-TOKEN": token, "Content-Type": "application/json"}
    }, (res3) => {
      let data3 = "";
      res3.on("data", d => data3 += d);
      res3.on("end", () => {
        let items = JSON.parse(data3).items;
        if (items) {
           console.log("Regular lessons:", items.map(i => ({ day: i.day, time_from: i.time_from, time_to: i.time_to, room: i.room_id })));
        } else {
           console.log("Regular lessons error:", data3);
        }
      });
    });
    req3.write(JSON.stringify({ "teacher_id": 20 }));
    req3.end();
  });
});
req.write(JSON.stringify({email: "aramgrigoryan2k4@gmail.com", api_key: "70cc373b-bed2-11f0-bfab-3cecefbdd1ae"}));
req.end();

