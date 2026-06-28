import { Hero } from "@/components/guest/hero";
import { Gallery } from "@/components/guest/gallery";
import { RoomsBooking } from "@/components/guest/rooms-booking";
import { LocationReviews } from "@/components/guest/location-reviews";
import { allRoomPhotos, galleryPhotos, heroPhoto } from "@/lib/photos";

// Read public/photos on each request so newly dropped photos show without a rebuild.
// ponytail: local fs read is cheap; switch to static + revalidate if traffic ever warrants.
export const dynamic = "force-dynamic";

export default function GuestLandingPage() {
  return (
    <>
      <Hero photo={heroPhoto()} />
      <Gallery photos={galleryPhotos()} />
      <RoomsBooking roomPhotos={allRoomPhotos()} />
      <LocationReviews />
    </>
  );
}
