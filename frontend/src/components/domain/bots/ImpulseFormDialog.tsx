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
import { useCreateImpulse } from "@/hooks/queries/useImpulses";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";
import type { ImpulseAction } from "@/api/endpoints/impulses";

const ACTIONS: ImpulseAction[] = [
  "PAUSE_BOT",
  "CLOSE_POSITION",
  "INCREASE_RISK",
  "DECREASE_RISK",
  "OTHER",
];

// M7 "Diario de impulsos", boton "Tengo el impulso de intervenir" (7.4):
// mismo patron de dialogo minimo con estado local que PostponeDialog (G6),
// sin RHF -- 2 campos simples, no justifica el peso de un schema Zod.
export function ImpulseFormDialog({
  botId,
  botName,
  open,
  onOpenChange,
}: {
  botId: number;
  botName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [description, setDescription] = useState("");
  const [action, setAction] = useState<ImpulseAction>("PAUSE_BOT");
  const [success, setSuccess] = useState(false);
  const createImpulse = useCreateImpulse();

  function handleSubmit() {
    createImpulse.mutate(
      { bot_id: botId, description, desired_action: action },
      {
        onSuccess: () => {
          setSuccess(true);
          setDescription("");
        },
      }
    );
  }

  function handleOpenChange(next: boolean) {
    if (!next) setSuccess(false);
    onOpenChange(next);
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {interpolate(uiStrings.bots.impulseDialogTitle, { bot: botName })}
          </DialogTitle>
        </DialogHeader>
        {success ? (
          <p className="text-sm text-semantic-success">{uiStrings.bots.impulseSuccess}</p>
        ) : (
          <div className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="impulse-description">
                {uiStrings.bots.impulseDescriptionLabel}
              </Label>
              <textarea
                id="impulse-description"
                className="min-h-20 w-full rounded-md border border-border-subtle bg-bg-app px-3 py-2 text-sm text-text-primary"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="impulse-action">{uiStrings.bots.impulseActionLabel}</Label>
              <select
                id="impulse-action"
                className="w-full rounded-md border border-border-subtle bg-bg-app px-3 py-2 text-sm text-text-primary"
                value={action}
                onChange={(e) => setAction(e.target.value as ImpulseAction)}
              >
                {ACTIONS.map((value) => (
                  <option key={value} value={value}>
                    {(uiStrings.bots.impulseActions as Record<string, string>)[value]}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            {uiStrings.bots.impulseCancel}
          </Button>
          {!success && (
            <Button
              disabled={createImpulse.isPending || description.trim().length === 0}
              onClick={handleSubmit}
            >
              {uiStrings.bots.impulseSubmit}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
