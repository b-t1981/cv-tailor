const http = require("http");

const TARGET = "http://localhost:3000";
const PORT = 3030;

http
  .createServer((req, res) => {
    const location = `${TARGET}${req.url || "/"}`;
    res.writeHead(307, { Location: location });
    res.end();
  })
  .listen(PORT, () => {
    console.log(`Redirect actif : http://localhost:${PORT} -> ${TARGET}`);
  });
