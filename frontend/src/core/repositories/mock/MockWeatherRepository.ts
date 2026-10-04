import { IWeatherRepository, WeatherReport } from "../interfaces/WeatherRepository";
import { DEFAULT_WEATHER } from "./mockData";

export class MockWeatherRepository implements IWeatherRepository {
  async getWeatherForCoordinates(_lat: number, _lng: number): Promise<WeatherReport> {
    return { ...DEFAULT_WEATHER };
  }
}
