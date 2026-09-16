
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
        if(items) {
           console.log("Found lessons:", items.slice(0, 3).map(i => ({
               time_from: i.time_from, 
               time_to: i.time_to, 
               subject: i.subject_id, 
               room: i.room_id
           })));
        } else {
           console.log("No items", data2);
        }
      });
    });
    // Request lessons for teacher 20 for 16.09 to 18.09
    req2.write(JSON.stringify({ "teacher_id": 20, "date_from": "16.09.2026", "date_to": "18.09.2026" }));
    req2.end();
  });
});
req.write(JSON.stringify({email: "aramgrigoryan2k4@gmail.com", api_key: "70cc373b-bed2-11f0-bfab-3cecefbdd1ae"}));
req.end();

