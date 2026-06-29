"use client";

// Renders a /photos/* url as <video> or <img> by extension.
// ponytail: extension is the type discriminator; mirrors MEDIA_RE in photos.ts
// (that module is server-only, can't import here).
const VIDEO_RE = /\.(mp4|webm)$/i;

export function Media({
  src,
  alt = "",
  className,
  controls = false,
}: {
  src: string;
  alt?: string;
  className?: string;
  controls?: boolean;
}) {
  if (VIDEO_RE.test(src)) {
    return (
      <video
        src={src}
        className={className}
        muted
        loop
        autoPlay
        playsInline
        controls={controls}
      />
    );
  }
  // eslint-disable-next-line @next/next/no-img-element -- dynamic public photo
  return <img src={src} alt={alt} className={className} />;
}
