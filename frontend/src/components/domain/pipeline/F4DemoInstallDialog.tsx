import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { createPipelineWorkItem, requestPipelineCommand } from "@/api/endpoints/pipeline";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import uiStrings from "@/styles/ui_strings.es.json";

export function F4DemoInstallDialog({ candidateId, open, onOpenChange }: { candidateId: number; open: boolean; onOpenChange: (open: boolean) => void }) {
  const [sourceMq5, setSourceMq5] = useState("");
  const [expertPath, setExpertPath] = useState("");
  const [magicNumber, setMagicNumber] = useState("");
  const [profileName, setProfileName] = useState("");
  const [symbol, setSymbol] = useState("");
  const [timeframe, setTimeframe] = useState("");
  const install = useMutation({
    mutationFn: async () => {
      const item = await createPipelineWorkItem({ kind: "F4_DEMO_INSTALL", source_key: `candidate:${candidateId}`, phase: "F4", payload: { candidate_id: candidateId } });
      const demoPlan = { source_mq5: sourceMq5, symbol, timeframe, expert_relative_path: expertPath, magic_number: Number(magicNumber), profile_name: profileName, candidate_id: candidateId };
      const bytes = new TextEncoder().encode(JSON.stringify(demoPlan, Object.keys(demoPlan).sort()));
      const hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))).map((value) => value.toString(16).padStart(2, "0")).join("");
      return requestPipelineCommand(item.id, { command_type: "DEMO_INSTALL", confirmed: true, idempotency_key: crypto.randomUUID(), payload: { target_group: "CONTABO_INCUBATOR_DEMO", demo_plan: demoPlan, demo_plan_sha256: hash } });
    },
    onSuccess: () => onOpenChange(false),
  });
  const preview = { source_mq5: sourceMq5, symbol, timeframe, expert_relative_path: expertPath, magic_number: Number(magicNumber), profile_name: profileName, candidate_id: candidateId };
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent><DialogHeader><DialogTitle>{uiStrings.pipeline.f4InstallTitle}</DialogTitle></DialogHeader><p className="text-xs text-text-secondary">{uiStrings.pipeline.f4InstallDescription}</p><div className="space-y-2"><Label htmlFor="f4-source">{uiStrings.pipeline.f4SourceMq5}</Label><Input id="f4-source" value={sourceMq5} onChange={(event) => setSourceMq5(event.target.value)} /><Label htmlFor="f4-expert">{uiStrings.pipeline.f4ExpertPath}</Label><Input id="f4-expert" value={expertPath} onChange={(event) => setExpertPath(event.target.value)} /><Input placeholder="Símbolo MT5" value={symbol} onChange={(event) => setSymbol(event.target.value)} /><Input placeholder="Timeframe" value={timeframe} onChange={(event) => setTimeframe(event.target.value)} /><Label htmlFor="f4-magic">{uiStrings.pipeline.f4Magic}</Label><Input id="f4-magic" type="number" value={magicNumber} onChange={(event) => setMagicNumber(event.target.value)} /><Label htmlFor="f4-profile">{uiStrings.pipeline.f4Profile}</Label><Input id="f4-profile" value={profileName} onChange={(event) => setProfileName(event.target.value)} /><pre className="max-h-32 overflow-auto rounded bg-muted p-2 text-xs">{JSON.stringify(preview, null, 2)}</pre></div><DialogFooter><Button variant="outline" onClick={() => onOpenChange(false)}>{uiStrings.pipeline.f4InstallCancel}</Button><Button disabled={!sourceMq5 || !expertPath || !symbol || !timeframe || !magicNumber || !profileName || install.isPending} onClick={() => install.mutate()}>{uiStrings.pipeline.f4InstallConfirm}</Button></DialogFooter></DialogContent></Dialog>;
}
