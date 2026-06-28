// Server-only: resolves homestay photos from public/photos at request/build time.
// The owner just drops image files into the folders below — no code change needed.
//   public/photos/hero/            -> hero shot
//   public/photos/gallery/         -> gallery grid
//   public/photos/rooms/<room_number>/  -> per-room photos
// Do NOT import this from a client component (uses node:fs).
import fs from "node:fs";
import path from "node:path";

export const PLACEHOLDER = "/photos/placeholder.svg";

const IMAGE_RE = /\.(jpe?g|png|webp|avif)$/i;

/** Pure: keep images, sort by name, map to /photos/<subdir>/<file> urls. */
export function toPhotoUrls(filenames: string[], subdir: string): string[] {
  return filenames
    .filter((f) => IMAGE_RE.test(f))
    .sort()
    .map((f) => `/photos/${subdir}/${f}`);
}

function photosIn(subdir: string): string[] {
  try {
    const dir = path.join(process.cwd(), "public", "photos", subdir);
    return toPhotoUrls(fs.readdirSync(dir), subdir);
  } catch {
    return [];
  }
}

export function heroPhoto(): string {
  return photosIn("hero")[0] ?? PLACEHOLDER;
}

export function galleryPhotos(): string[] {
  const photos = photosIn("gallery");
  return photos.length ? photos : [PLACEHOLDER];
}

export function roomPhotos(roomNumber: string): string[] {
  const photos = photosIn(`rooms/${roomNumber}`);
  return photos.length ? photos : [PLACEHOLDER];
}
