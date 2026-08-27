import { useState } from "react";

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

function tomorrowDateInputValue(): string {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  return tomorrow.toISOString().slice(0, 10);
}

interface PostponeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (postponeUntil: string) => void;
  isPending: boolean;
}

// PostponeRequest.postpone_until es obligatorio en el backend (sin
// default) -- PARTE 7.1 no da el detalle exacto de este control en el
// panel de Resumen, asi que se diseña un modal minimo con un date-picker,
// default "+1 dia" preseleccionado (diseno propio, documentado en
// ASSUMPTIONS G6, reutilizable en G7 para otras pestanas).
export function PostponeDialog({ open, onOpenChange, onConfirm, isPending }: PostponeDialogProps) {
  const [date, setDate] = useState(tomorrowDateInputValue);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{uiStrings.decisionCard.postponeDialogTitle}</DialogTitle>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="postpone-date">{uiStrings.decisionCard.postponeDialogLabel}</Label>
          <Input
            id="postpone-date"
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {uiStrings.decisionCard.postponeDialogCancel}
          </Button>
          <Button
            disabled={isPending}
            onClick={() => onConfirm(new Date(date).toISOString())}
          >
            {uiStrings.decisionCard.postponeDialogSubmit}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
