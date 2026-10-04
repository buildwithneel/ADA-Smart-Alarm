import { MockAlarmRepository } from "./mock/MockAlarmRepository";
import { MockDestinationRepository } from "./mock/MockDestinationRepository";
import { MockETARepository } from "./mock/MockETARepository";
import { MockWeatherRepository } from "./mock/MockWeatherRepository";
import { MockActivityRepository } from "./mock/MockActivityRepository";

import { ApiAlarmRepository } from "./api/ApiAlarmRepository";
import { ApiDestinationRepository } from "./api/ApiDestinationRepository";
import { ApiETARepository } from "./api/ApiETARepository";
import { ApiContextRepository } from "./api/ApiContextRepository";
import { ApiCalendarRepository } from "./api/ApiCalendarRepository";

import { IAlarmRepository } from "./interfaces/AlarmRepository";
import { IDestinationRepository } from "./interfaces/DestinationRepository";
import { IETARepository } from "./interfaces/ETARepository";
import { IContextRepository } from "./interfaces/ContextRepository";
import { ICalendarRepository } from "./interfaces/CalendarRepository";

// Check environment flag for real API backend usage
const useRealApi = import.meta.env.VITE_USE_API === "true";

export const alarmRepository: IAlarmRepository = useRealApi
  ? new ApiAlarmRepository()
  : new MockAlarmRepository();

export const destinationRepository: IDestinationRepository = useRealApi
  ? new ApiDestinationRepository()
  : new MockDestinationRepository();

export const etaRepository: IETARepository = useRealApi
  ? new ApiETARepository()
  : new MockETARepository();

export const contextRepository: IContextRepository = new ApiContextRepository();
export const calendarRepository: ICalendarRepository = new ApiCalendarRepository();

export const weatherRepository = new MockWeatherRepository();
export const activityRepository = new MockActivityRepository();

export * from "./interfaces/AlarmRepository";
export * from "./interfaces/DestinationRepository";
export * from "./interfaces/ETARepository";
export * from "./interfaces/WeatherRepository";
export * from "./interfaces/ActivityRepository";
export * from "./interfaces/ContextRepository";
export * from "./interfaces/CalendarRepository";
export { ApiAlarmRepository } from "./api/ApiAlarmRepository";
export { ApiDestinationRepository } from "./api/ApiDestinationRepository";
export { ApiETARepository } from "./api/ApiETARepository";
export { ApiContextRepository } from "./api/ApiContextRepository";
export { ApiCalendarRepository } from "./api/ApiCalendarRepository";

