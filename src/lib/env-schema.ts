import { z } from "zod"

export const envSchema = z.object({
  NEXT_PUBLIC_ASAP_PROTOCOL_URL: z
    .string()
    .optional()
    .transform((v) => (v ? v : "https://asap-protocol.vercel.app"))
    .pipe(z.string().url()),
})

export type EnvSchema = z.infer<typeof envSchema>

export function parseEnv(input: Record<string, string | undefined>): EnvSchema {
  const parsed = envSchema.safeParse(input)
  if (!parsed.success) {
    throw new Error(
      `Invalid environment variables: ${parsed.error.message}. ` +
        "Ensure NEXT_PUBLIC_ASAP_PROTOCOL_URL is a valid URL when set.",
    )
  }
  return parsed.data
}
