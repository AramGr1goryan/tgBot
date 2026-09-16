
const https = require("https");
const req = https.request("https://robixlab.s20.online/v2api/auth/login", {
  method: "POST", headers: {"Content-Type": "application/json"}
}, (res) => {
  let data = "";
  res.on("data", d => data += d);
  res.on("end", () => {
    const token = JSON.parse(data).token;
    const req2 = https.request("https://robixlab.s20.online/v2api/1/room/index", {
      method: "POST", headers: {"X-ALFACRM-TOKEN": token}
    }, (res2) => {
      let data2 = "";
      res2.on("data", d => data2 += d);
      res2.on("end", () => {
        const rooms = JSON.parse(data2).items;
        rooms.forEach(r => console.log("ID", r.id, r.name, "Loc:", r.location_id));
      });
    });
    req2.end();
  });
});
req.write(JSON.stringify({email: "aramgrigoryan2k4@gmail.com", api_key: "70cc373b-bed2-11f0-bfab-3cecefbdd1ae"}));
req.end();

