/**
 * CesiumJS dış uçuş — Puppeteer ile kare render edilir.
 * Google Photorealistic 3D Tiles veya 2D uydu/harita fallback kullanır.
 *
 * Kullanım:
 *   node exterior_shot.js --lat 39.9 --lng 32.8 --duration 30 --fps 25 --output /tmp/ext_frames
 *
 * Not: Cesium tarayıcıda çalışır — bu script Puppeteer aracılığıyla HTML sayfası yükler.
 */

const puppeteer = require("puppeteer");
const fs = require("fs");
const path = require("path");

const args = process.argv.slice(2);
const getArg = (name, def = "") => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : def;
};

const LAT = parseFloat(getArg("--lat", "39.9"));
const LNG = parseFloat(getArg("--lng", "32.8"));
const DURATION = parseInt(getArg("--duration", "15"));
const FPS = parseInt(getArg("--fps", "25"));
const OUTPUT_DIR = getArg("--output", "/tmp/ext_frames");
const WIDTH = parseInt(getArg("--width", "1920"));
const HEIGHT = parseInt(getArg("--height", "1080"));
const GOOGLE_3D_TILES_KEY = process.env.GOOGLE_MAPS_API_KEY || "";

const CESIUM_HTML = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Cesium Exterior</title>
  <script src="https://cesium.com/downloads/cesiumjs/releases/1.118/Build/Cesium/Cesium.js"></script>
  <link rel="stylesheet" href="https://cesium.com/downloads/cesiumjs/releases/1.118/Build/Cesium/Widgets/widgets.css"/>
  <style>html,body,#cesiumContainer{width:100%;height:100%;margin:0;padding:0;overflow:hidden;}</style>
</head>
<body>
  <div id="cesiumContainer"></div>
  <script>
    Cesium.Ion.defaultAccessToken = '${process.env.CESIUM_ION_TOKEN || ""}';

    const viewer = new Cesium.Viewer('cesiumContainer', {
      timeline: false, animation: false, baseLayerPicker: false,
      navigationHelpButton: false, sceneModePicker: false,
      geocoder: false, homeButton: false, fullscreenButton: false,
      infoBox: false, selectionIndicator: false,
    });

    ${GOOGLE_3D_TILES_KEY ? `
    // Google Photorealistic 3D Tiles
    try {
      const tileset = await Cesium.Cesium3DTileset.fromUrl(
        'https://tile.googleapis.com/v1/3dtiles/root.json?key=${GOOGLE_3D_TILES_KEY}'
      );
      viewer.scene.primitives.add(tileset);
      console.log('3D_TILES_LOADED');
    } catch(e) {
      console.log('3D_TILES_FAILED: ' + e.message);
    }
    ` : `
    // Fallback: Bing/OpenStreetMap 2D
    viewer.imageryLayers.addImageryProvider(
      new Cesium.OpenStreetMapImageryProvider({url: 'https://a.tile.openstreetmap.org/'})
    );
    console.log('2D_FALLBACK');
    `}

    // Uçuş animasyonu
    const LAT = ${LAT}, LNG = ${LNG};
    window._cesiumReady = false;

    async function startFlight() {
      // Yüksekten yaklaşım
      await viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(LNG, LAT - 0.002, 600),
        orientation: { heading: Cesium.Math.toRadians(0), pitch: Cesium.Math.toRadians(-30), roll: 0 },
        duration: ${DURATION * 0.4},
      });
      // Yakın çekim orbit
      viewer.camera.lookAt(
        Cesium.Cartesian3.fromDegrees(LNG, LAT, 0),
        new Cesium.HeadingPitchRange(Cesium.Math.toRadians(0), Cesium.Math.toRadians(-20), 200)
      );
      window._cesiumReady = true;
    }
    startFlight();
  </script>
</body>
</html>`;

async function renderExteriorShot() {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  // HTML'i geçici dosyaya yaz
  const htmlPath = path.join(OUTPUT_DIR, "cesium.html");
  fs.writeFileSync(htmlPath, CESIUM_HTML);

  const browser = await puppeteer.launch({
    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || undefined,
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"],
    headless: true,
  });

  const page = await browser.newPage();
  await page.setViewport({ width: WIDTH, height: HEIGHT });
  await page.goto(`file://${htmlPath}`, { waitUntil: "networkidle0", timeout: 30000 });

  // Cesium yüklenene kadar bekle (max 10s)
  await page.waitForFunction(() => window._cesiumReady === true, { timeout: 10000 }).catch(() => {
    console.warn("Cesium tam yüklenmedi — fallback");
  });

  const totalFrames = FPS * DURATION;
  const framePaths = [];

  for (let frame = 0; frame < totalFrames; frame++) {
    const framePath = path.join(OUTPUT_DIR, `frame_${String(frame).padStart(5, "0")}.png`);
    await page.screenshot({ path: framePath });
    framePaths.push(framePath);

    if (frame % FPS === 0) {
      const progress = Math.round((frame / totalFrames) * 100);
      console.log(JSON.stringify({ frame, total: totalFrames, progress }));
    }
  }

  await browser.close();

  console.log(JSON.stringify({
    status: "done",
    frames: framePaths.length,
    output_dir: OUTPUT_DIR,
  }));
}

renderExteriorShot().catch((err) => {
  console.error("Exterior render hatası:", err.message);
  process.exit(1);
});
