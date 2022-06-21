// const http = require("http");
const express = require("express");

PORT = 3000;
// Response is a JSON object
// POST, GET. or CREATE, READ
// create a block on blockchain
// POST /API/ block
// send back block and acknowledge if verified
// GET /API/ block / <block id>
// send back all blocks on blockchain
// GET /API/ blocks
const server = http.createServer((req, res) => {
  if (req.url === "/") {
    // ...
    res.write("Hello World");
    res.end();
  }
  if (req.url === "/block") {
  }
});

server.listen(PORT);

// Separate functions should handle connection to server.
