import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import {
  registerDemoAttachment,
  type DemoAttachmentManifestInput,
  type DemoReadiness,
} from "@/api/endpoints/pipeline";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import uiStrings from "@/styles/ui_strings.es.json";

type FormField = Exclude<keyof DemoAttachmentManifestInput, "required_mode" | "required_autotrading">;

const fields: Array<{ key: FormField; inputType?: "number" | "text" }> = [
  { key: "asset_id", inputType: "number" },
  { key: "account_login" },
  { key: "magic_number", inputType: "number" },
  { key: "symbol" },
  { key: "timeframe" },
  { key: "ea_version" },
  { key: "mql5_sha256" },
  { key: "compiled_ex5_sha256" },
  { key: "comment_identity" },
  { key: "expert_relative_path" },
  { key: "reporter_outbox" },
  { key: "required_sizing_pct", inputType: "number" },
];

export function DemoAttachmentDialog({
  candidateId,
  open,
  onOpenChange,
  onRegistered,
}: {
  candidateId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRegistered: (readiness: DemoReadiness) => void;
}) {
  const [values, setValues] = useState<Record<FormField, string>>(
    () => Object.fromEntries(fields.map(({ key }) => [key, ""])) as Record<FormField, string>
  );
  const register = useMutation({
    mutationFn: (manifest: DemoAttachmentManifestInput) => registerDemoAttachment(candidateId, manifest),
    onSuccess: (readiness) => {
      onRegistered(readiness);
      onOpenChange(false);
    },
  });

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    register.mutate({
      ...values,
      asset_id: Number(values.asset_id),
      magic_number: Number(values.magic_number),
      required_mode: "REAL",
      required_autotrading: true,
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{uiStrings.pipeline.demoAttachmentTitle}</DialogTitle>
        </DialogHeader>
        <form className="space-y-3" onSubmit={submit}>
          <p className="text-xs text-text-secondary">{uiStrings.pipeline.demoAttachmentDescription}</p>
          <div className="grid max-h-96 grid-cols-1 gap-2 overflow-y-auto pr-1">
            {fields.map(({ key, inputType = "text" }) => (
              <div className="space-y-1" key={key}>
                <Label htmlFor={`demo-attachment-${key}`}>
                  {uiStrings.pipeline.demoAttachmentFields[key]}
                </Label>
                <Input
                  id={`demo-attachment-${key}`}
                  type={inputType}
                  step={key === "required_sizing_pct" ? "0.01" : undefined}
                  min={inputType === "number" ? "0" : undefined}
                  required
                  value={values[key]}
                  onChange={(event) => setValues((current) => ({ ...current, [key]: event.target.value }))}
                />
              </div>
            ))}
          </div>
          {register.isError && <p className="text-xs text-semantic-danger">{uiStrings.pipeline.demoAttachmentError}</p>}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              {uiStrings.pipeline.demoAttachmentCancel}
            </Button>
            <Button type="submit" disabled={register.isPending}>
              {uiStrings.pipeline.demoAttachmentSubmit}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
