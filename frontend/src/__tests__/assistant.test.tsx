// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { AIStatusIndicator } from "@/components/assistant/AIStatusIndicator";
import { AssistantMessage } from "@/components/assistant/AssistantMessage";
import { MissingInformationPrompt } from "@/components/assistant/MissingInformationPrompt";
import { AssistantInput } from "@/components/assistant/AssistantInput";
import { AlarmDraftPreview } from "@/components/assistant/AlarmDraftPreview";
import { AlarmDraft, AssistantStatus } from "@/core/types/assistant";

// Mock localStorage if missing
class MockLocalStorage {
  private store: Record<string, string> = {};
  getItem(key: string) {
    return this.store[key] || null;
  }
  setItem(key: string, val: string) {
    this.store[key] = val;
  }
  removeItem(key: string) {
    delete this.store[key];
  }
  clear() {
    this.store = {};
  }
}

if (typeof window !== "undefined" && !window.localStorage) {
  // @ts-ignore
  window.localStorage = new MockLocalStorage();
}

describe("Step 11: AI Assistant & Personalization Frontend Components", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe("AIStatusIndicator", () => {
    it("renders loading state cleanly", () => {
      render(<AIStatusIndicator status={null} isLoading={true} />);
      expect(screen.getByText("Connecting to ADA Assistant...")).toBeDefined();
    });

    it("renders online status with active provider", () => {
      const mockStatus: AssistantStatus = {
        status: "online",
        provider: "mock",
        model: "ada-deterministic-nlp-v1",
        features: ["intent_extraction", "clarifications", "draft_generation"],
      };

      render(
        <BrowserRouter>
          <AIStatusIndicator status={mockStatus} isLoading={false} />
        </BrowserRouter>
      );

      expect(screen.getByText("AI Assistant Ready")).toBeDefined();
      expect(screen.getByText("mock")).toBeDefined();
      expect(screen.getByText("Standard Form")).toBeDefined();
    });

    it("renders fallback status when provider is offline", () => {
      const mockStatus: AssistantStatus = {
        status: "fallback",
        provider: "deterministic",
        model: "standard-rules-v1",
        features: ["deterministic_fallback"],
      };

      render(
        <BrowserRouter>
          <AIStatusIndicator status={mockStatus} isLoading={false} />
        </BrowserRouter>
      );

      expect(screen.getByText("Deterministic Engine Active")).toBeDefined();
      expect(screen.getByText("deterministic")).toBeDefined();
    });
  });

  describe("AssistantMessage", () => {
    it("renders user message bubble aligned to the right", () => {
      const msg = {
        id: "msg_1",
        role: "user" as const,
        content: "I need to reach CHARUSAT by 9 AM tomorrow.",
        created_at: new Date().toISOString(),
      };

      render(<AssistantMessage message={msg} userName="Neel" />);
      expect(screen.getByText("Neel")).toBeDefined();
      expect(screen.getByText("I need to reach CHARUSAT by 9 AM tomorrow.")).toBeDefined();
    });

    it("renders assistant message with ADA branding and formatted lines", () => {
      const msg = {
        id: "msg_2",
        role: "assistant" as const,
        content: "Here is your draft schedule:\n• Wake up at 07:45 AM\n• Leave by 08:15 AM",
        created_at: new Date().toISOString(),
      };

      render(<AssistantMessage message={msg} />);
      expect(screen.getByText("ADA Assistant")).toBeDefined();
      expect(screen.getByText("Here is your draft schedule:")).toBeDefined();
      expect(screen.getByText("Wake up at 07:45 AM")).toBeDefined();
      expect(screen.getByText("Leave by 08:15 AM")).toBeDefined();
    });
  });

  describe("MissingInformationPrompt", () => {
    it("returns null when no fields or questions are missing", () => {
      const { container } = render(
        <MissingInformationPrompt
          missingFields={[]}
          clarificationQuestions={[]}
          onSelectSuggestion={() => {}}
        />
      );
      expect(container.firstChild).toBeNull();
    });

    it("renders clarification list and quick suggestion buttons", () => {
      const onSelect = vi.fn();
      render(
        <MissingInformationPrompt
          missingFields={["destination", "arrival_time"]}
          clarificationQuestions={[
            "Where are you traveling to?",
            "What time do you need to arrive?",
          ]}
          onSelectSuggestion={onSelect}
        />
      );

      expect(screen.getByText("Where are you traveling to?")).toBeDefined();
      expect(screen.getByText("What time do you need to arrive?")).toBeDefined();

      const charusatBtn = screen.getByText("CHARUSAT University");
      expect(charusatBtn).toBeDefined();
      fireEvent.click(charusatBtn);
      expect(onSelect).toHaveBeenCalledWith("Destination is CHARUSAT University");
    });
  });

  describe("AssistantInput", () => {
    it("allows typing and submitting via button", async () => {
      const onSend = vi.fn().mockResolvedValue(undefined);
      render(<AssistantInput onSendMessage={onSend} />);

      const textarea = screen.getByRole("textbox", { name: /natural language alarm prompt/i });
      fireEvent.change(textarea, { target: { value: "Wake me up at 7am tomorrow" } });

      const sendBtn = screen.getByRole("button", { name: /send/i });
      expect(sendBtn).toBeDefined();
      fireEvent.click(sendBtn);

      expect(onSend).toHaveBeenCalledWith("Wake me up at 7am tomorrow");
    });

    it("supports clicking starter prompt pills", () => {
      const onSend = vi.fn().mockResolvedValue(undefined);
      render(<AssistantInput onSendMessage={onSend} />);

      const starterBtn = screen.getByText(
        "I need to reach CHARUSAT by 9 AM tomorrow. 30m prep, 10m buffer."
      );
      fireEvent.click(starterBtn);

      const textarea = screen.getByRole("textbox", {
        name: /natural language alarm prompt/i,
      }) as HTMLTextAreaElement;
      expect(textarea.value).toBe(
        "I need to reach CHARUSAT by 9 AM tomorrow. 30m prep, 10m buffer."
      );
    });

    it("disables send button when input is empty or loading", () => {
      const onSend = vi.fn().mockResolvedValue(undefined);
      render(<AssistantInput onSendMessage={onSend} isLoading={true} />);

      const textarea = screen.getByRole("textbox", {
        name: /natural language alarm prompt/i,
      }) as HTMLTextAreaElement;
      expect(textarea.disabled).toBe(true);
    });
  });

  describe("AlarmDraftPreview", () => {
    const mockDraft: AlarmDraft = {
      id: "draft_test_123",
      user_id: 1,
      title: "Trip to CHARUSAT",
      destination_text: "CHARUSAT, Changa",
      destination_place_id: "place_123",
      destination_latitude: 22.5996,
      destination_longitude: 72.8205,
      arrival_time: "09:00:00",
      arrival_date: "2026-10-05",
      timezone: "Asia/Kolkata",
      preparation_time: 30,
      safety_buffer: 10,
      transportation_mode: "driving",
      travel_duration_minutes: 35,
      traffic_delay_minutes: 0,
      estimated_travel_duration: 35,
      estimated_distance_meters: 25000,
      recommended_leave_time: "08:15:00",
      recommended_wake_time: "07:45:00",
      grounded_explanation:
        "Leave at 08:15 AM because destination ETA is 35 minutes and you selected a 10-minute safety buffer. Wake up at 07:45 AM for 30 minutes of preparation.",
      status: "draft",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    it("renders deterministic schedule milestones", () => {
      render(
        <BrowserRouter>
          <AlarmDraftPreview
            draft={mockDraft}
            onConfirm={vi.fn()}
            onUpdate={vi.fn()}
            onDiscard={vi.fn()}
          />
        </BrowserRouter>
      );

      expect(screen.getByText("Trip to CHARUSAT")).toBeDefined();
      expect(screen.getByText("CHARUSAT, Changa")).toBeDefined();
      expect(screen.getByText("07:45")).toBeDefined(); // Wake up
      expect(screen.getByText("08:15")).toBeDefined(); // Leave
      expect(screen.getByText(/08:50/)).toBeDefined(); // Planned arrival (09:00 - 10m buffer)
      expect(screen.getByText("09:00")).toBeDefined(); // Deadline
      expect(screen.getByText(/Leave at 08:15 AM because destination ETA is 35 minutes/i)).toBeDefined();
    });

    it("calls onConfirm with idempotency key when user clicks Confirm & Schedule", async () => {
      const onConfirm = vi.fn().mockResolvedValue(undefined);
      render(
        <BrowserRouter>
          <AlarmDraftPreview
            draft={mockDraft}
            onConfirm={onConfirm}
            onUpdate={vi.fn()}
            onDiscard={vi.fn()}
          />
        </BrowserRouter>
      );

      const confirmBtn = screen.getByRole("button", { name: /confirm & schedule alarm/i });
      fireEvent.click(confirmBtn);

      expect(onConfirm).toHaveBeenCalled();
      const [draftId, idempotencyKey] = onConfirm.mock.calls[0];
      expect(draftId).toBe("draft_test_123");
      expect(idempotencyKey).toBeDefined();
      expect(typeof idempotencyKey).toBe("string");
      expect(idempotencyKey.length).toBeGreaterThan(10);
    });

    it("calls onDiscard when user clicks Discard", () => {
      const onDiscard = vi.fn().mockResolvedValue(undefined);
      render(
        <BrowserRouter>
          <AlarmDraftPreview
            draft={mockDraft}
            onConfirm={vi.fn()}
            onUpdate={vi.fn()}
            onDiscard={onDiscard}
          />
        </BrowserRouter>
      );

      const discardBtns = screen.getAllByRole("button", { name: /discard/i });
      fireEvent.click(discardBtns[0]);
      expect(onDiscard).toHaveBeenCalledWith("draft_test_123");
    });
  });
});
