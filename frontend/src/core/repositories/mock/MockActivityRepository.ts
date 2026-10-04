import { ActivityEvent, IActivityRepository } from "../interfaces/ActivityRepository";
import { INITIAL_ACTIVITIES } from "./mockData";

export class MockActivityRepository implements IActivityRepository {
  private activities: ActivityEvent[] = [...INITIAL_ACTIVITIES];

  async getAll(): Promise<ActivityEvent[]> {
    return [...this.activities];
  }

  async logEvent(event: Omit<ActivityEvent, "id" | "timestamp">): Promise<ActivityEvent> {
    const newEvent: ActivityEvent = {
      ...event,
      id: `act-${Date.now()}`,
      timestamp: "Just now",
    };
    this.activities.unshift(newEvent);
    return { ...newEvent };
  }
}
