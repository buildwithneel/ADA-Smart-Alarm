export interface WeatherReport {
  condition: string;
  temperatureC: number;
  precipitationProbability: number;
  commuteImpact: "none" | "low" | "moderate" | "severe";
  recommendedBufferMinutes: number;
}

export interface IWeatherRepository {
  getWeatherForCoordinates(lat: number, lng: number): Promise<WeatherReport>;
}
