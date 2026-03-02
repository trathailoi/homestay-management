"use client";

import { useState } from "react";
import api from "@/lib/api";
import { useTranslation } from "@/lib/language-context";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface CreateRoomDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
}

export function CreateRoomDialog({ open, onOpenChange, onCreated }: CreateRoomDialogProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { t } = useTranslation();

  const [roomNumber, setRoomNumber] = useState("");
  const [roomType, setRoomType] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [maxOccupancy, setMaxOccupancy] = useState("");
  const [basePricePerNight, setBasePricePerNight] = useState("");
  const [amenities, setAmenities] = useState("");

  function resetForm() {
    setRoomNumber("");
    setRoomType("");
    setName("");
    setDescription("");
    setMaxOccupancy("");
    setBasePricePerNight("");
    setAmenities("");
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const amenitiesList = amenities
        .split(",")
        .map((a) => a.trim())
        .filter((a) => a.length > 0);

      await api.post("/rooms", {
        room_number: roomNumber,
        room_type: roomType,
        name,
        description: description || undefined,
        max_occupancy: parseInt(maxOccupancy, 10),
        base_price_per_night: parseFloat(basePricePerNight),
        amenities: amenitiesList.length > 0 ? amenitiesList : undefined,
      });

      resetForm();
      onOpenChange(false);
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("createRoom.createFailed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t("createRoom.title")}</DialogTitle>
          <DialogDescription>
            {t("createRoom.description")}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="roomNumber">{t("createRoom.roomNumber")}</Label>
              <Input
                id="roomNumber"
                value={roomNumber}
                onChange={(e) => setRoomNumber(e.target.value)}
                placeholder={t("createRoom.roomNumberPlaceholder")}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="roomType">{t("createRoom.roomType")}</Label>
              <Input
                id="roomType"
                value={roomType}
                onChange={(e) => setRoomType(e.target.value)}
                placeholder={t("createRoom.roomTypePlaceholder")}
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="name">{t("createRoom.name")}</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("createRoom.namePlaceholder")}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">{t("createRoom.description_field")}</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t("createRoom.descriptionPlaceholder")}
              rows={3}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="maxOccupancy">{t("createRoom.maxOccupancy")}</Label>
              <Input
                id="maxOccupancy"
                type="number"
                min="1"
                value={maxOccupancy}
                onChange={(e) => setMaxOccupancy(e.target.value)}
                placeholder={t("createRoom.maxOccupancyPlaceholder")}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="basePricePerNight">{t("createRoom.pricePerNight")}</Label>
              <Input
                id="basePricePerNight"
                type="number"
                min="0"
                step="0.01"
                value={basePricePerNight}
                onChange={(e) => setBasePricePerNight(e.target.value)}
                placeholder={t("createRoom.pricePerNightPlaceholder")}
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="amenities">{t("createRoom.amenities")}</Label>
            <Input
              id="amenities"
              value={amenities}
              onChange={(e) => setAmenities(e.target.value)}
              placeholder={t("createRoom.amenitiesPlaceholder")}
            />
          </div>

          {error && (
            <div className="rounded-md bg-red-50 dark:bg-red-950 p-3 text-sm text-red-600 dark:text-red-400">
              {error}
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? t("createRoom.creating") : t("createRoom.createRoom")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
