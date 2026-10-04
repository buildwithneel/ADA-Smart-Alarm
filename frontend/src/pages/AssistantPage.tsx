import { useSearchParams } from "react-router-dom";
import { AssistantPanel } from "@/components/assistant/AssistantPanel";

export function AssistantPage() {
  const [searchParams] = useSearchParams();
  const initialPrompt = searchParams.get("prompt") || "";

  return (
    <div className="w-full">
      <AssistantPanel initialPrompt={initialPrompt} />
    </div>
  );
}
