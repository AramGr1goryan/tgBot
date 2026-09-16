
const https = require("https");

const req = https.request("https://robixlab.s20.online/v2api/auth/login", {
  method: "POST",
  headers: {"Content-Type": "application/json"}
}, (res) => {
  let data = "";
  res.on("data", d => data += d);
  res.on("end", () => {
    const token = JSON.parse(data).token;
    
    // Fetch Branch 2 lessons
    const body = JSON.stringify({date_from: "2026-09-14", date_to: "2026-09-20", status: 1, "per-page": 100});
    const req2 = https.request("https://robixlab.s20.online/v2api/2/lesson/index", {
      method: "POST",
      headers: {"X-ALFACRM-TOKEN": token, "Content-Type": "application/json"}
    }, (res2) => {
      let data2 = "";
      res2.on("data", d => data2 += d);
      res2.on("end", () => {
        const lessons = JSON.parse(data2).items || [];
        const branches = new Set(lessons.map(l => l.branch_id));
        console.log("Branch IDs for /v2api/2/lesson/index:", Array.from(branches));
        if(lessons.length > 0) {
            console.log("First lesson:", lessons[0].id, "Branch:", lessons[0].branch_id);
        }
      });
    });
    req2.write(body);
    req2.end();
  });
});
req.write(JSON.stringify({email: "aramgrigoryan2k4@gmail.com", api_key: "70cc373b-bed2-11f0-bfab-3cecefbdd1ae"}));
req.end();

