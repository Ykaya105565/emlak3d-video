import { Composition } from "remotion";
import { InteriorGML } from "./compositions/InteriorGML";
import { ExteriorScene } from "./compositions/ExteriorScene";
import { InteriorPhoto } from "./compositions/InteriorPhoto";
import { InteriorData } from "./compositions/InteriorData";
import { VillaHayali } from "./compositions/VillaHayali";

const DEFAULT_FPS = 25;
const DEFAULT_DURATION = 30;

export function RemotionRoot() {
  const durationInFrames = (parseInt(process.env.RENDER_DURATION || String(DEFAULT_DURATION))) * DEFAULT_FPS;

  return (
    <>
      <Composition
        id="InteriorGML"
        component={InteriorGML}
        durationInFrames={durationInFrames}
        fps={DEFAULT_FPS}
        width={1920}
        height={1080}
        defaultProps={{
          inventoryJson: "{}",
          gltfPath: "",
          audioPath: "",
          isWatermarked: true,
        }}
      />
      <Composition
        id="ExteriorScene"
        component={ExteriorScene}
        durationInFrames={durationInFrames}
        fps={DEFAULT_FPS}
        width={1920}
        height={1080}
        defaultProps={{
          exteriorFramesDir: "",
          lat: 39.9,
          lng: 32.8,
          audioPath: "",
          isWatermarked: true,
        }}
      />
      <Composition
        id="InteriorPhoto"
        component={InteriorPhoto}
        durationInFrames={durationInFrames}
        fps={DEFAULT_FPS}
        width={1920}
        height={1080}
        defaultProps={{
          photoUrls: [],
          listingData: "{}",
          audioPath: "",
          isWatermarked: true,
        }}
      />
      <Composition
        id="InteriorData"
        component={InteriorData}
        durationInFrames={durationInFrames}
        fps={DEFAULT_FPS}
        width={1920}
        height={1080}
        defaultProps={{
          listingData: "{}",
          audioPath: "",
          isWatermarked: true,
        }}
      />
      <Composition
        id="VillaHayali"
        component={VillaHayali}
        durationInFrames={durationInFrames}
        fps={DEFAULT_FPS}
        width={1920}
        height={1080}
        defaultProps={{
          envelopeJson: "{}",
          frameUrl: "",
          audioPath: "",
          isWatermarked: true,
          listingData: "{}",
        }}
      />
    </>
  );
}
