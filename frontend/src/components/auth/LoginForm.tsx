import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { login } from "@/api/endpoints/auth";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/stores/authStore";
import uiStrings from "@/styles/ui_strings.es.json";
import { PasswordRecoveryDialog } from "@/components/auth/PasswordRecoveryDialog";

function buildLoginSchema() {
  return z.object({
    email: z.string().email(uiStrings.login.emailInvalid),
    password: z.string().min(1, uiStrings.login.passwordRequired),
  });
}

type LoginValues = z.infer<ReturnType<typeof buildLoginSchema>>;

export function LoginForm() {
  const navigate = useNavigate();
  const setSession = useAuthStore((state) => state.setSession);
  const form = useForm<LoginValues>({
    resolver: zodResolver(buildLoginSchema()),
    defaultValues: { email: "", password: "" },
  });

  const mutation = useMutation({
    mutationFn: (values: LoginValues) => login(values.email, values.password),
    onSuccess: (tokens) => {
      setSession(tokens.access_token, tokens.refresh_token);
      navigate("/", { replace: true });
    },
  });

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
        className="w-full max-w-sm space-y-4"
      >
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{uiStrings.login.emailLabel}</FormLabel>
              <FormControl>
                <Input type="email" autoComplete="username" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>{uiStrings.login.passwordLabel}</FormLabel>
              <FormControl>
                <Input type="password" autoComplete="current-password" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {mutation.isError && (
          <p className="text-sm text-semantic-danger">{uiStrings.login.credentialsInvalid}</p>
        )}
        <Button type="submit" className="w-full" disabled={mutation.isPending}>
          {uiStrings.login.submit}
        </Button>
        <PasswordRecoveryDialog />
      </form>
    </Form>
  );
}
