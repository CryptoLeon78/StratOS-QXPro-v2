import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { requestPipelineCommand, type PipelineWorkItem } from "@/api/endpoints/pipeline";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import uiStrings from "@/styles/ui_strings.es.json";

export type F1Action = "FORJA_GENERATE" | "SQX_START" | "SQX_STOP";

const actionLabels: Record<F1Action, string> = {
  FORJA_GENERATE: uiStrings.pipeline.generateForja,
  SQX_START: uiStrings.pipeline.startSqx,
  SQX_STOP: uiStrings.pipeline.stopSqx,
};

export function F1ActionDialog({
  action,
  item,
  open,
  onOpenChange,
}: {
  action: F1Action | null;
  item: PipelineWorkItem | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const [entryId, setEntryId] = useState("");
  const [projectPath, setProjectPath] = useState("");
  const [base, setBase] = useState("forja");
  const [layer, setLayer] = useState("capa1");
  const [direction, setDirection] = useState("LS");
  const enqueue = useMutation({
    mutationFn: () => {
      if (item === null || action === null) throw new Error("F1 action is unavailable");
      const payload: Record<string, unknown> = { target_group: "ANALYSIS" };
      if (action === "FORJA_GENERATE") {
        Object.assign(payload, { entry_id: entryId, base, capa: layer, direccion: direction });
      } else {
        Object.assign(payload, { project_path: projectPath });
      }
      return requestPipelineCommand(item.id, {
        command_type: action,
        payload,
        idempotency_key: crypto.randomUUID(),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipeline-work-items", "F1"] });
      onOpenChange(false);
    },
  });
  const forja = action === "FORJA_GENERATE";
  const enabled = item !== null && action !== null && (forja ? entryId.trim().length > 0 : projectPath.trim().length > 0);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{uiStrings.pipeline.f1ActionTitle}</DialogTitle>
          <DialogDescription>{uiStrings.pipeline.f1ActionDescription}</DialogDescription>
        </DialogHeader>
        <p className="text-sm text-text-secondary">{action ? actionLabels[action] : ""}</p>
        {forja ? (
          <div className="space-y-3">
            <div className="space-y-1">
              <Label htmlFor="f1-catalog-entry">{uiStrings.pipeline.f1CatalogEntry}</Label>
              <Input id="f1-catalog-entry" value={entryId} onChange={(event) => setEntryId(event.target.value)} />
            </div>
            <div className="grid grid-cols-3 gap-2">
              <label className="space-y-1 text-sm text-text-primary">
                {uiStrings.pipeline.f1Base}
                <select className="w-full rounded-md border border-border-subtle bg-bg-surface p-2" value={base} onChange={(event) => setBase(event.target.value)}>
                  <option value="forja">forja</option>
                  <option value="principal">principal</option>
                </select>
              </label>
              <label className="space-y-1 text-sm text-text-primary">
                {uiStrings.pipeline.f1Layer}
                <select className="w-full rounded-md border border-border-subtle bg-bg-surface p-2" value={layer} onChange={(event) => setLayer(event.target.value)}>
                  <option value="capa1">capa1</option>
                  <option value="capa2">capa2</option>
                </select>
              </label>
              <label className="space-y-1 text-sm text-text-primary">
                {uiStrings.pipeline.f1Direction}
                <select className="w-full rounded-md border border-border-subtle bg-bg-surface p-2" value={direction} onChange={(event) => setDirection(event.target.value)}>
                  <option value="L">L</option>
                  <option value="S">S</option>
                  <option value="LS">LS</option>
                </select>
              </label>
            </div>
          </div>
        ) : (
          <div className="space-y-1">
            <Label htmlFor="f1-project-path">{uiStrings.pipeline.f1ProjectPath}</Label>
            <Input id="f1-project-path" value={projectPath} onChange={(event) => setProjectPath(event.target.value)} />
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>{uiStrings.pipeline.f1ActionCancel}</Button>
          <Button disabled={!enabled || enqueue.isPending} onClick={() => enqueue.mutate()}>{uiStrings.pipeline.f1ActionEnqueue}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
