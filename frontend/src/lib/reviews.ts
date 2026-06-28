// Hand-picked guest reviews. Quotes kept in their original language (Vietnamese).
//
// TODO(owner): replace the placeholders below with real quotes from the
// Google Maps listing's Review section:
// https://www.google.com/maps/place/nhà+nghỉ+View+Biển/@12.3844064,109.3187473,17z
export type Review = {
  name: string;
  rating: number; // 1–5
  text: string;
};

export const reviews: Review[] = [
  {
    name: "Khách Google",
    rating: 5,
    text: "View biển tuyệt đẹp, phòng sạch sẽ và chủ nhà rất thân thiện. Sẽ quay lại!",
  },
  {
    name: "Khách Google",
    rating: 5,
    text: "Không gian yên tĩnh, gần biển, buổi sáng thức dậy nghe tiếng sóng rất thư giãn.",
  },
  {
    name: "Khách Google",
    rating: 4,
    text: "Vị trí đẹp, đồ ăn ngon. Đường ra đảo hơi xa nhưng rất đáng để trải nghiệm.",
  },
];

// Place: Nhà nghỉ View Biển, Ninh Vân (12.3844064, 109.3187473)
export const GOOGLE_MAPS_URL =
  "https://www.google.com/maps/place/nh%C3%A0+ngh%E1%BB%89+View+Bi%E1%BB%83n/@12.3844064,109.3187473,17z/data=!4m7!3m6!1s0x31706d004e66f15b:0xc37007ccfec282b6!8m2!3d12.3844064!4d109.3187473!16s%2Fg%2F11ydcck9z7";

// Keyless embed (no Maps API key required).
export const MAP_EMBED_URL =
  "https://maps.google.com/maps?q=12.3844064,109.3187473&z=16&hl=vi&output=embed";
