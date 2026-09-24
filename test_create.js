const https = require('https');

async function doRequest(url, method, headers, data) {
    return new Promise((resolve, reject) => {
        const u = new URL(url);
        const options = {
            hostname: u.hostname,
            port: 443,
            path: u.pathname + u.search,
            method: method,
            headers: headers
        };
        const req = https.request(options, (res) => {
            let body = '';
            res.on('data', chunk => body += chunk);
            res.on('end', () => resolve({statusCode: res.statusCode, body: body}));
        });
        req.on('error', reject);
        if (data) {
            req.write(JSON.stringify(data));
        }
        req.end();
    });
}

async function main() {
    let authRes = await doRequest('https://robixlab.s20.online/v2api/auth/login', 'POST', {'Content-Type': 'application/json'}, {email: 'aram.g.gn@gmail.com', api_key: 'a10d9223-3db4-11ef-be7a-3cecef6687ac'});
    let token = JSON.parse(authRes.body).token;
    let headers = {'X-ALFACRM-TOKEN': token, 'Content-Type': 'application/json'};
    
    let payload = {
        lesson_type_id: 3,
        date: '2026-09-21',
        time_from: '15:00',
        time_to: '15:50',
        subject_id: 23,
        room_id: 34,
        customer_ids: [2451], // random assumed id
        status: 1
    };
    
    console.log("Testing with date");
    let res = await doRequest('https://robixlab.s20.online/v2api/1/lesson/create', 'POST', headers, payload);
    console.log(res.statusCode, res.body);
    
    let payload2 = {...payload};
    delete payload2.date;
    payload2.date_from = '2026-09-21';
    payload2.date_to = '2026-09-21';
    
    console.log("\nTesting with date_from/date_to");
    let res2 = await doRequest('https://robixlab.s20.online/v2api/1/lesson/create', 'POST', headers, payload2);
    console.log(res2.statusCode, res2.body);
}

main();
