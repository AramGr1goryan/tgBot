const fs = require('fs');

let c = fs.readFileSync('c:\\tgbot\\api\\webhook.py', 'utf8');

const h_start = c.indexOf('@dp.message(Command("check"))');
const h_end = c.indexOf('@app.post("/api/webhook")');
const handler = c.substring(h_start, h_end);

// Remove the handler from the end
c = c.substring(0, h_start) + c.substring(h_end);

// Find process_payment
const target_idx = c.indexOf('async def process_payment');
if (target_idx !== -1) {
    // Find the decorator above it
    const decorator_idx = c.lastIndexOf('@dp.message', target_idx);
    c = c.substring(0, decorator_idx) + handler + "\n" + c.substring(decorator_idx);
    fs.writeFileSync('c:\\tgbot\\api\\webhook.py', c, 'utf8');
    console.log("successfully moved");
} else {
    console.log("could not find process_payment");
}
