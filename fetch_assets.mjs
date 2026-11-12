// Downloads the CC0 Poly Haven assets used by build.py into ./assets
import fs from "fs";
import path from "path";
const A = "assets";
const HDRI = ["qwantani_sunset_puresky", "belfast_sunset_puresky", "kloppenheim_06_puresky", "evening_road_01_puresky"];
const TEX = ["castle_brick_broken_06", "medieval_blocks_05", "large_sandstone_blocks", "rock_tile_floor", "cobblestone_floor_08",
  "grass_path_2", "aerial_grass_rock", "forrest_ground_01", "weathered_planks", "rock_face_03", "metal_plate", "rusty_metal_02", "marble_01", "old_sandstone_02", "mossy_sandstone", "rock_surface", "sandstone_cracks", "grass_ground", "leafy_grass", "sparse_grass"];
const MODELS = ["grass_medium_01", "grass_medium_02", "namaqualand_boulder_02", "namaqualand_cliff_01", "boulder_01", "rock_moss_set_01",
  "wooden_ladder", "dandelion_01", "shrub_01", "wooden_crate_02", "ammo_box", "old_military_crate", "namaqualand_stones_01", "coast_land_rocks_02",
  "fir_sapling", "pine_sapling_small", "fir_sapling_medium", "shrub_02", "shrub_04"];
async function dl(url, dest) {
  if (fs.existsSync(dest) && fs.statSync(dest).size > 0) return;
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  const r = await fetch(url);
  if (!r.ok) throw new Error(r.status + " " + url);
  fs.writeFileSync(dest, Buffer.from(await r.arrayBuffer()));
  console.log("got", dest);
}
const files = async (id) => (await fetch("https://api.polyhaven.com/files/" + id)).json();
for (const id of HDRI) { const f = await files(id); await dl(f.hdri["4k"].hdr.url, `${A}/hdri/${id}.hdr`); }
for (const id of TEX) {
  const f = await files(id);
  for (const [key, name] of [["Diffuse", "diff"], ["nor_gl", "nor"], ["Rough", "rough"], ["Displacement", "disp"], ["AO", "ao"]]) {
    const e = f[key]?.["2k"]; if (!e) { console.log("no", key, id); continue; }
    const v = e.jpg || e.png; await dl(v.url, `${A}/tex/${id}_${name}${path.extname(v.url)}`);
  }
}
for (const id of MODELS) {
  const f = await files(id);
  const g = (f.gltf["2k"] || f.gltf["1k"]).gltf;
  await dl(g.url, `${A}/models/${id}/${id}.gltf`);
  for (const [rel, inc] of Object.entries(g.include || {})) await dl(inc.url, `${A}/models/${id}/${rel}`);
}
console.log("done");
