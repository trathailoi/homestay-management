import { describe, expect, it } from "vitest";
import { PLACEHOLDER, roomPhotos, toPhotoUrls } from "./photos";

describe("toPhotoUrls", () => {
  it("keeps only images, sorts, and maps to public urls", () => {
    expect(
      toPhotoUrls(["b.JPG", "a.png", "notes.txt", "c.webp", ".gitkeep"], "gallery"),
    ).toEqual([
      "/photos/gallery/a.png",
      "/photos/gallery/b.JPG",
      "/photos/gallery/c.webp",
    ]);
  });

  it("returns empty when no images present", () => {
    expect(toPhotoUrls(["readme.md", ".gitkeep"], "hero")).toEqual([]);
  });
});

describe("fallback", () => {
  it("roomPhotos falls back to the placeholder for an unknown room", () => {
    expect(roomPhotos("no-such-room")).toEqual([PLACEHOLDER]);
  });
});
