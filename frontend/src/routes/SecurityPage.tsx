import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { changePassword, getRecoveryStatus } from "@/api/endpoints/auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { interpolate } from "@/lib/i18n";
import { useAuthStore } from "@/stores/authStore";
import uiStrings from "@/styles/ui_strings.es.json";

export default function SecurityPage() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const setSession = useAuthStore((state) => state.setSession);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const status = useQuery({ queryKey: ["recovery-status"], queryFn: getRecoveryStatus });
  const change = useMutation({
    mutationFn: () => changePassword(currentPassword, newPassword, accessToken ?? ""),
    onSuccess: (tokens) => setSession(tokens.access_token, tokens.refresh_token),
  });
  const passwordsMatch = newPassword === confirmation;
  const minimumPasswordLength = status.data?.minimum_password_length ?? 0;

  return (
    <main className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
      <div>
        <h2 className="text-xl font-semibold text-text-primary">{uiStrings.security.title}</h2>
        <p className="mt-1 text-sm text-text-secondary">{uiStrings.security.description}</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>{uiStrings.security.recoveryTitle}</CardTitle>
          <CardDescription>{uiStrings.security.recoveryDescription}</CardDescription>
        </CardHeader>
        <CardContent>
          {status.isLoading ? <p className="text-sm text-text-secondary">{uiStrings.app.loadingTab}</p> : (
            <p className={status.data?.configured ? "text-sm text-semantic-success" : "text-sm text-semantic-warning"}>
              {status.data?.configured ? uiStrings.security.recoveryReady : uiStrings.security.recoveryMissing}
            </p>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>{uiStrings.security.changeTitle}</CardTitle>
          <CardDescription>{uiStrings.security.changeDescription}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <label className="grid gap-1 text-sm text-text-secondary">
            {uiStrings.security.currentPasswordLabel}
            <Input type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} autoComplete="current-password" />
          </label>
          <label className="grid gap-1 text-sm text-text-secondary">
            {uiStrings.security.newPasswordLabel}
            <Input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} autoComplete="new-password" />
          </label>
          <p className="text-sm text-text-secondary">
            {interpolate(uiStrings.security.passwordMinimum, { count: minimumPasswordLength })}
          </p>
          <label className="grid gap-1 text-sm text-text-secondary">
            {uiStrings.security.confirmPasswordLabel}
            <Input type="password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} autoComplete="new-password" />
          </label>
          {!passwordsMatch && confirmation && <p className="text-sm text-semantic-danger">{uiStrings.security.passwordMismatch}</p>}
          {change.isError && <p className="text-sm text-semantic-danger">{uiStrings.security.changeError}</p>}
          {change.isSuccess && <p className="text-sm text-semantic-success">{uiStrings.security.changeSuccess}</p>}
          <Button type="button" onClick={() => change.mutate()} disabled={!currentPassword || newPassword.length < minimumPasswordLength || !passwordsMatch || change.isPending}>
            {uiStrings.security.changeSubmit}
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
