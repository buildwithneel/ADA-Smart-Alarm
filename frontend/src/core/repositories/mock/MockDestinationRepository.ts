import { Destination, IDestinationRepository } from "../interfaces/DestinationRepository";
import { INITIAL_DESTINATIONS } from "./mockData";

export class MockDestinationRepository implements IDestinationRepository {
  private destinations: Destination[] = [...INITIAL_DESTINATIONS];

  async getAll(): Promise<Destination[]> {
    return [...this.destinations];
  }

  async getById(id: string): Promise<Destination | null> {
    const found = this.destinations.find((d) => d.id === id);
    return found ? { ...found } : null;
  }

  async create(input: Omit<Destination, "id">): Promise<Destination> {
    const newDest: Destination = {
      ...input,
      id: `dest-${Date.now()}`,
    };
    this.destinations.push(newDest);
    return { ...newDest };
  }

  async update(id: string, input: Partial<Destination>): Promise<Destination> {
    const index = this.destinations.findIndex((d) => d.id === id);
    if (index === -1) throw new Error(`Destination ${id} not found`);
    this.destinations[index] = { ...this.destinations[index], ...input };
    return { ...this.destinations[index] };
  }

  async toggleFavorite(id: string): Promise<Destination> {
    const dest = await this.getById(id);
    if (!dest) throw new Error(`Destination ${id} not found`);
    return this.update(id, { isFavorite: !dest.isFavorite });
  }

  async delete(id: string): Promise<boolean> {
    const len = this.destinations.length;
    this.destinations = this.destinations.filter((d) => d.id !== id);
    return this.destinations.length < len;
  }
}
