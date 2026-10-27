/**
 * Deterministic Journey State Machine.
 * Enforces valid state transitions and triggers for destination-aware tracking.
 */

import { JourneyAlertEvent, JourneyState } from "../contracts/models.js";

export interface JourneyTransitionResult {
  nextState: JourneyState;
  alertEvent?: JourneyAlertEvent;
  isValid: boolean;
  errorReason?: string;
}

export class JourneyStateMachine {
  /**
   * Evaluates a proposed transition from currentState given a new status or event.
   */
  static transition(
    currentState: JourneyState,
    event: {
      type: "START_TRACKING" | "FIX_DEGRADED" | "FIX_RESTORED" | "DEVIATION" | "APPROACHING" | "ARRIVED" | "CANCEL";
      hasAlertedApproaching?: boolean;
    }
  ): JourneyTransitionResult {
    // Terminal states cannot transition further
    if (currentState === JourneyState.ARRIVED || currentState === JourneyState.CANCELLED || currentState === JourneyState.FAILED) {
      if (event.type === "CANCEL") {
        return { nextState: currentState, isValid: true };
      }
      return {
        nextState: currentState,
        isValid: false,
        errorReason: `Cannot transition from terminal state: ${currentState}`,
      };
    }

    switch (event.type) {
      case "START_TRACKING":
        if (currentState === JourneyState.SCHEDULED || currentState === JourneyState.READY_TO_TRACK) {
          return {
            nextState: JourneyState.ACTIVE_TRACKING,
            alertEvent: JourneyAlertEvent.TRACKING_STARTED,
            isValid: true,
          };
        }
        return { nextState: currentState, isValid: true };

      case "FIX_DEGRADED":
        return {
          nextState: JourneyState.TRACKING_DEGRADED,
          alertEvent: JourneyAlertEvent.TRACKING_DEGRADED,
          isValid: true,
        };

      case "FIX_RESTORED":
        if (currentState === JourneyState.TRACKING_DEGRADED) {
          return {
            nextState: JourneyState.ACTIVE_TRACKING,
            isValid: true,
          };
        }
        return { nextState: currentState, isValid: true };

      case "DEVIATION":
        return {
          nextState: JourneyState.RECALCULATING,
          alertEvent: JourneyAlertEvent.ROUTE_DEVIATED,
          isValid: true,
        };

      case "APPROACHING":
        if (!event.hasAlertedApproaching) {
          return {
            nextState: JourneyState.APPROACHING,
            alertEvent: JourneyAlertEvent.APPROACHING_ALERT,
            isValid: true,
          };
        }
        return { nextState: JourneyState.APPROACHING, isValid: true };

      case "ARRIVED":
        return {
          nextState: JourneyState.ARRIVED,
          alertEvent: JourneyAlertEvent.ARRIVAL_CONFIRMED,
          isValid: true,
        };

      case "CANCEL":
        return {
          nextState: JourneyState.CANCELLED,
          isValid: true,
        };

      default:
        return { nextState: currentState, isValid: true };
    }
  }
}
