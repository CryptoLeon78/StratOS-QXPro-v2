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
import { usePipelineActions } from "@/hooks/queries/usePipelineActions";
import { interpolate } from "@/lib/i18n";
import uiStrings from "@/styles/ui_strings.es.json";

const CAUSES = Object.keys(uiStrings.graveyard.causes) as (keyof typeof uiStrings.graveyard.causes)[];

// PARTE 6.3 "KILL abre formulario de autopsia bloqueante": cause/
// autopsy_text/lesson son obligatorios en el backend, sin defaults --
// reutiliza el catalogo de CemeteryCause ya traducido para Graveyard.
export function KillDialog({
  candidateId,
  botName,
  open,
  onOpenChange,
}: {
  candidateId: number;
  botName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [cause, setCause] = useState(CAUSES[0]);
  const [autopsyText, setAutopsyText] = useState("");
  const [lesson, setLesson] = useState("");
  const { kill } = usePipelineActions();

  function handleSubmit() {
    kill.mutate(
      { candidateId, body: { cause, autopsy_text: autopsyText, lesson } },
      { onSuccess: () => onOpenChange(false) }
    );
  }

  const canSubmit = autopsyText.trim().length > 0 && lesson.trim().length > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{interpolate(uiStrings.pipeline.killDialogTitle, { bot: botName })}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="kill-cause">{uiStrings.pipeline.causeLabel}</Label>
            <select
              id="kill-cause"
              className="w-full rounded-md border border-border-subtle bg-bg-app px-3 py-2 text-sm text-text-primary"
              value={cause}
              onChange={(e) => setCause(e.target.value as typeof cause)}
            >
              {CAUSES.map((value) => (
                <option key={value} value={value}>
                  {uiStrings.graveyard.causes[value]}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="kill-autopsy">{uiStrings.pipeline.autopsyLabel}</Label>
            <textarea
              id="kill-autopsy"
              className="min-h-16 w-full rounded-md border border-border-subtle bg-bg-app px-3 py-2 text-sm text-text-primary"
              value={autopsyText}
              onChange={(e) => setAutopsyText(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="kill-lesson">{uiStrings.pipeline.lessonLabel}</Label>
            <textarea
              id="kill-lesson"
              className="min-h-16 w-full rounded-md border border-border-subtle bg-bg-app px-3 py-2 text-sm text-text-primary"
              value={lesson}
              onChange={(e) => setLesson(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {uiStrings.pipeline.killCancel}
          </Button>
          <Button variant="destructive" disabled={!canSubmit || kill.isPending} onClick={handleSubmit}>
            {uiStrings.pipeline.killSubmit}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
