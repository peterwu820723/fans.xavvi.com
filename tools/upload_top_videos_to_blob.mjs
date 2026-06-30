import { createReadStream, existsSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { extname } from "node:path";
import { put } from "@vercel/blob";

const DATA_PATH = "data/top_videos.json";
const JS_PATH = "data/top_videos.js";
const MANIFEST_PATH = "outputs/blob-upload-manifest.json";
const PREFIX = "top-videos";

function loadEnvFile(path = ".env.local") {
  if (!existsSync(path)) return;
  const lines = readFileSync(path, "utf8").split(/\r?\n/);
  for (const line of lines) {
    const match = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)\s*$/);
    if (!match || process.env[match[1]]) continue;
    process.env[match[1]] = match[2].replace(/^["']|["']$/g, "");
  }
}

function contentType(path) {
  switch (extname(path).toLowerCase()) {
    case ".mp4":
      return "video/mp4";
    case ".webp":
      return "image/webp";
    case ".jpg":
    case ".jpeg":
      return "image/jpeg";
    case ".png":
      return "image/png";
    default:
      return "application/octet-stream";
  }
}

function loadJson(path, fallback) {
  if (!existsSync(path)) return fallback;
  return JSON.parse(readFileSync(path, "utf8"));
}

function saveJson(path, value) {
  writeFileSync(path, JSON.stringify(value, null, 2), "utf8");
}

function blobPath(localPath) {
  return `${PREFIX}/${localPath.replace(/^assets[\\/]+top-videos[\\/]+/, "").replaceAll("\\", "/")}`;
}

async function uploadFile(localPath, manifest, token) {
  if (manifest[localPath]?.url) return manifest[localPath].url;
  if (!existsSync(localPath)) throw new Error(`Missing file: ${localPath}`);

  const pathname = blobPath(localPath);
  const result = await put(pathname, createReadStream(localPath), {
    access: "public",
    addRandomSuffix: false,
    multipart: true,
    contentType: contentType(localPath),
    token,
  });

  manifest[localPath] = {
    url: result.url,
    pathname,
    bytes: statSync(localPath).size,
  };
  saveJson(MANIFEST_PATH, manifest);
  return result.url;
}

function collectFiles(data) {
  const files = [];
  for (const videos of Object.values(data)) {
    for (const video of videos) {
      files.push(video.video, video.thumbnail);
    }
  }
  return [...new Set(files)].filter(Boolean);
}

async function main() {
  loadEnvFile();
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) {
    throw new Error("Missing BLOB_READ_WRITE_TOKEN. Run `vercel env pull .env.local` first.");
  }

  const data = loadJson(DATA_PATH, {});
  const manifest = loadJson(MANIFEST_PATH, {});
  const files = collectFiles(data);
  let uploaded = 0;

  for (const file of files) {
    const url = await uploadFile(file, manifest, token);
    uploaded += 1;
    if (uploaded % 25 === 0 || uploaded === files.length) {
      console.log(`uploaded ${uploaded}/${files.length}`);
    }
  }

  for (const videos of Object.values(data)) {
    for (const video of videos) {
      video.video = manifest[video.video]?.url || video.video;
      video.thumbnail = manifest[video.thumbnail]?.url || video.thumbnail;
    }
  }

  saveJson(DATA_PATH, data);
  writeFileSync(JS_PATH, `window.TOP_VIDEOS = ${JSON.stringify(data)};\n`, "utf8");
  console.log(`updated ${DATA_PATH} and ${JS_PATH}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
