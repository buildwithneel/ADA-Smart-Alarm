import apiClient from "@/core/api/apiClient";
import {
  Destination,
  DestinationCategory,
  IDestinationRepository,
} from "../interfaces/DestinationRepository";

interface BackendDestination {
  id: string;
  user_id: string;
  name: string;
  type: string;
  latitude: number;
  longitude: number;
  address: string;
  place_id?: string | null;
  provider?: string | null;
  is_favorite: boolean;
  created_at: string;
  updated_at: string;
}

export class ApiDestinationRepository implements IDestinationRepository {
  private mapFromBackend(item: BackendDestination): Destination {
    return {
      id: item.id,
      name: item.name,
      category: (item.type.toLowerCase() as DestinationCategory) || "custom",
      address: item.address,
      latitude: item.latitude,
      longitude: item.longitude,
      isFavorite: item.is_favorite,
      defaultTransportMode: "driving",
      defaultBufferMinutes: 15,
      defaultRoutineMinutes: 30,
    };
  }

  async getAll(): Promise<Destination[]> {
    const response = await apiClient.get<BackendDestination[]>("/destinations");
    return response.data.map(this.mapFromBackend);
  }

  async getById(id: string): Promise<Destination | null> {
    try {
      const response = await apiClient.get<BackendDestination>(`/destinations/${id}`);
      return this.mapFromBackend(response.data);
    } catch {
      return null;
    }
  }

  async create(input: Omit<Destination, "id">): Promise<Destination> {
    const payload = {
      name: input.name,
      type: input.category,
      latitude: input.latitude,
      longitude: input.longitude,
      address: input.address,
      is_favorite: input.isFavorite,
    };
    const response = await apiClient.post<BackendDestination>("/destinations", payload);
    return this.mapFromBackend(response.data);
  }

  async update(id: string, input: Partial<Destination>): Promise<Destination> {
    const payload: Record<string, unknown> = {};
    if (input.name !== undefined) payload.name = input.name;
    if (input.category !== undefined) payload.type = input.category;
    if (input.latitude !== undefined) payload.latitude = input.latitude;
    if (input.longitude !== undefined) payload.longitude = input.longitude;
    if (input.address !== undefined) payload.address = input.address;
    if (input.isFavorite !== undefined) payload.is_favorite = input.isFavorite;

    const response = await apiClient.patch<BackendDestination>(`/destinations/${id}`, payload);
    return this.mapFromBackend(response.data);
  }

  async toggleFavorite(id: string): Promise<Destination> {
    const current = await this.getById(id);
    if (!current) throw new Error(`Destination ${id} not found.`);
    return this.update(id, { isFavorite: !current.isFavorite });
  }

  async delete(id: string): Promise<boolean> {
    try {
      await apiClient.delete(`/destinations/${id}`);
      return true;
    } catch {
      return false;
    }
  }
}
