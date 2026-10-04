import { TransportMode } from "@/core/types/alarm";

export type DestinationCategory = "home" | "college" | "office" | "gym" | "airport" | "custom";

export interface Destination {
  id: string;
  name: string;
  category: DestinationCategory;
  address: string;
  latitude: number;
  longitude: number;
  isFavorite: boolean;
  defaultTransportMode: TransportMode;
  defaultBufferMinutes: number;
  defaultRoutineMinutes: number;
}

export interface IDestinationRepository {
  getAll(): Promise<Destination[]>;
  getById(id: string): Promise<Destination | null>;
  create(input: Omit<Destination, "id">): Promise<Destination>;
  update(id: string, input: Partial<Destination>): Promise<Destination>;
  toggleFavorite(id: string): Promise<Destination>;
  delete(id: string): Promise<boolean>;
}
