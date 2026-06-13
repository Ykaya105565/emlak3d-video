/**
 * Three.js oda yürüyüşü — Puppeteer ile render edilir ve PNG kareler üretir.
 * Girdi: --gltf <dosya.glb> --inventory <inventory.json> --fps 25 --duration 30 --output <klasör>
 *
 * Kullanım:
 *   node interior_walk.js --gltf model.glb --inventory inv.json --fps 25 --duration 30 --output /tmp/frames
 */

const THREE = require("three");
const { GLTFLoader } = require("three/examples/jsm/loaders/GLTFLoader.js");
const fs = require("fs");
const path = require("path");

// CLI argümanlarını parse et
const args = process.argv.slice(2);
const getArg = (name) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : null;
};

const GLTF_PATH = getArg("--gltf");
const INVENTORY_PATH = getArg("--inventory");
const FPS = parseInt(getArg("--fps") || "25");
const DURATION = parseInt(getArg("--duration") || "30");
const OUTPUT_DIR = getArg("--output") || "/tmp/interior_frames";
const WIDTH = parseInt(getArg("--width") || "1920");
const HEIGHT = parseInt(getArg("--height") || "1080");
const EYE_HEIGHT = 1.6; // metre — göz hizası

/** Tur noktalarını oda centroid'lerinden oluştur */
function buildTourWaypoints(inventory) {
  const rooms = inventory.rooms || [];

  // Tur sırası
  const PRIORITY = {
    "Hol": 0, "Koridor": 1, "Salon": 2,
    "Mutfak": 3, "Kiler": 4,
    "Oda": 5, "Yatak Odası": 5, "Çocuk Odası": 5,
    "Balkon": 6, "Teras": 6,
    "Banyo": 7, "WC": 8,
    "Merdiven": 9,
  };

  const sorted = [...rooms].sort((a, b) => {
    const pa = PRIORITY[a.usage] ?? PRIORITY[a.name] ?? 5;
    const pb = PRIORITY[b.usage] ?? PRIORITY[b.name] ?? 5;
    if (pa !== pb) return pa - pb;
    return a.floor - b.floor;
  });

  return sorted.map((room) => ({
    roomId: room.id,
    roomName: room.name,
    area_m2: room.area_m2,
    floor: room.floor,
    position: new THREE.Vector3(
      (room.centroid_wgs84?.[1] ?? 0) * 111320,  // lng → metre (yaklaşık)
      EYE_HEIGHT + room.floor * 3.1,
      -(room.centroid_wgs84?.[0] ?? 0) * 111320  // lat → metre
    ),
  }));
}

/** Catmull-Rom spline ile yumuşak kamera yolu */
function buildCameraSpline(waypoints) {
  const pts = waypoints.map((w) => w.position);
  // Başa ve sona tekrar ekle (smooth başlangıç/bitiş)
  const extended = [pts[0].clone(), ...pts, pts[pts.length - 1].clone()];
  return new THREE.CatmullRomCurve3(extended, false, "catmullrom", 0.5);
}

/** Belirli t anında kamera bakış yönü */
function getCameraTarget(spline, t, lookahead = 0.02) {
  const next_t = Math.min(t + lookahead, 1.0);
  return spline.getPoint(next_t);
}

/**
 * Puppeteer olmadan çalışan "headless" Three.js render.
 * Gerçek sistemde @remotion/renderer veya Puppeteer ile ekran görüntüsü alınır.
 * Burada kamera pozisyonları + tur verisi JSON olarak çıktılanır (geliştirme modu).
 */
async function renderInteriorWalk() {
  if (!INVENTORY_PATH || !fs.existsSync(INVENTORY_PATH)) {
    console.error("Inventory JSON bulunamadı:", INVENTORY_PATH);
    process.exit(1);
  }

  const inventory = JSON.parse(fs.readFileSync(INVENTORY_PATH, "utf8"));
  const waypoints = buildTourWaypoints(inventory);

  if (waypoints.length === 0) {
    console.error("Tur noktası bulunamadı — inventory boş");
    process.exit(1);
  }

  const spline = buildCameraSpline(waypoints);
  const totalFrames = FPS * DURATION;

  // Kamera keyframe'lerini hesapla
  const keyframes = [];
  for (let frame = 0; frame < totalFrames; frame++) {
    const t = frame / (totalFrames - 1);
    const pos = spline.getPoint(t);
    const target = getCameraTarget(spline, t);

    // Mevcut odayı belirle
    const progress = t * (waypoints.length - 1);
    const roomIdx = Math.min(Math.floor(progress), waypoints.length - 1);
    const currentRoom = waypoints[roomIdx];

    keyframes.push({
      frame,
      t: parseFloat(t.toFixed(4)),
      camera: {
        x: parseFloat(pos.x.toFixed(3)),
        y: parseFloat(pos.y.toFixed(3)),
        z: parseFloat(pos.z.toFixed(3)),
      },
      target: {
        x: parseFloat(target.x.toFixed(3)),
        y: parseFloat(target.y.toFixed(3)),
        z: parseFloat(target.z.toFixed(3)),
      },
      room: currentRoom.roomName,
      room_area: currentRoom.area_m2,
      floor: currentRoom.floor,
    });
  }

  // Çıktı
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  const keyframesPath = path.join(OUTPUT_DIR, "camera_keyframes.json");
  fs.writeFileSync(keyframesPath, JSON.stringify({ keyframes, waypoints: waypoints.map(w => ({
    roomName: w.roomName,
    area_m2: w.area_m2,
    floor: w.floor,
    position: { x: w.position.x, y: w.position.y, z: w.position.z }
  }))}, null, 2));

  console.log(JSON.stringify({
    status: "keyframes_ready",
    output: keyframesPath,
    total_frames: totalFrames,
    rooms_visited: waypoints.length,
    duration_seconds: DURATION,
    fps: FPS,
  }));
}

renderInteriorWalk().catch((err) => {
  console.error("Render hatası:", err);
  process.exit(1);
});
