import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import {
  confirmPasswordRecovery,
  getRecoveryStatus,
  requestPasswordRecovery,
} from "@/api/endpoints/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import uiStrings from "@/styles/ui_strings.es.json";

export function PasswordRecoveryDialog() {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const status = useQuery({ queryKey: ["recovery-status"], queryFn: getRecoveryStatus, enabled: open });
  const request = useMutation({ mutationFn: () => requestPasswordRecovery(email) });
  const confirm = useMutation({
    mutationFn: () => confirmPasswordRecovery(email, code, newPassword),
    onSuccess: () => setConfirmed(true),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="link" type="button" className="px-0 text-sm">
          {uiStrings.recovery.open}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{uiStrings.recovery.title}</DialogTitle>
          <DialogDescription>{uiStrings.recovery.description}</DialogDescription>
        </DialogHeader>
        {status.data?.configured === false ? (
          <p className="text-sm text-semantic-warning">{uiStrings.recovery.notConfigured}</p>
        ) : confirmed ? (
          <p className="text-sm text-semantic-success">{uiStrings.recovery.success}</p>
        ) : (
          <div className="space-y-3">
            <label className="grid gap-1 text-sm text-text-secondary">
              {uiStrings.recovery.emailLabel}
              <Input type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
            </label>
            <Button type="button" className="w-full" onClick={() => request.mutate()} disabled={!email || request.isPending}>
              {request.isSuccess ? uiStrings.recovery.requested : uiStrings.recovery.requestCode}
            </Button>
            {request.isSuccess && <p className="text-sm text-text-secondary">{uiStrings.recovery.requestNotice}</p>}
            <label className="grid gap-1 text-sm text-text-secondary">
              {uiStrings.recovery.codeLabel}
              <Input value={code} onChange={(event) => setCode(event.target.value)} inputMode="numeric" />
            </label>
            <label className="grid gap-1 text-sm text-text-secondary">
              {uiStrings.recovery.newPasswordLabel}
              <Input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} autoComplete="new-password" />
            </label>
            {confirm.isError && <p className="text-sm text-semantic-danger">{uiStrings.recovery.invalidCode}</p>}
            <Button type="button" className="w-full" onClick={() => confirm.mutate()} disabled={!code || newPassword.length < (status.data?.minimum_password_length ?? 0) || confirm.isPending}>
              {uiStrings.recovery.confirm}
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
