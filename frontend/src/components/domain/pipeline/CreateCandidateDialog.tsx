import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { useBots } from "@/hooks/queries/useBots";
import { usePipelineBoard } from "@/hooks/queries/usePipelineBoard";
import { usePipelineActions } from "@/hooks/queries/usePipelineActions";
import uiStrings from "@/styles/ui_strings.es.json";

export function CreateCandidateDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { data: bots } = useBots();
  const { data: board } = usePipelineBoard();
  const { create } = usePipelineActions();
  const candidateBotIds = new Set((board ?? []).map((c) => c.bot_id));
  const eligible = (bots ?? []).filter((bot) => !candidateBotIds.has(bot.id));
  const [botId, setBotId] = useState<number | null>(null);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{uiStrings.pipeline.createDialogTitle}</DialogTitle>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="create-candidate-bot">{uiStrings.pipeline.createBotLabel}</Label>
          <select
            id="create-candidate-bot"
            className="w-full rounded-md border border-border-subtle bg-bg-app px-3 py-2 text-sm text-text-primary"
            value={botId ?? ""}
            onChange={(e) => setBotId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="" disabled>
              —
            </option>
            {eligible.map((bot) => (
              <option key={bot.id} value={bot.id}>
                {bot.name}
              </option>
            ))}
          </select>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {uiStrings.pipeline.createCancel}
          </Button>
          <Button
            disabled={botId === null || create.isPending}
            onClick={() =>
              botId !== null &&
              create.mutate(botId, { onSuccess: () => onOpenChange(false) })
            }
          >
            {uiStrings.pipeline.createSubmit}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
