/**
 * Render worker HTTP sunucusu (Express).
 * Python pipeline'a (pipeline.py) geçiş yapılan hafif proxy.
 * Port 8001.
 */

require("dotenv").config({ path: "/app/.env" });
const express = require("express");
const { spawn } = require("child_process");

const app = express();
app.use(express.json({ limit: "10mb" }));
const PORT = process.env.RENDER_WORKER_PORT || 8001;

app.get("/health", (req, res) => res.json({ status: "ok", worker: "render" }));

// Python pipeline'a delege et
app.post("/render", (req, res) => {
  const python = spawn("python3", ["src/pipeline.py"], {
    env: { ...process.env },
    cwd: "/app",
  });

  let stdout = "";
  let stderr = "";

  python.stdin.write(JSON.stringify(req.body));
  python.stdin.end();

  python.stdout.on("data", (d) => (stdout += d.toString()));
  python.stderr.on("data", (d) => (stderr += d.toString()));

  python.on("close", (code) => {
    if (code !== 0) {
      return res.status(500).json({ error: stderr.slice(-2000) });
    }
    try {
      res.json(JSON.parse(stdout));
    } catch {
      res.status(500).json({ error: "Pipeline çıktısı parse edilemedi", raw: stdout.slice(-500) });
    }
  });
});

app.listen(PORT, () => {
  console.log(`Render worker hazır: http://0.0.0.0:${PORT}`);
});
