import { z } from "zod";
import type { SessionAuthorityInfo } from "~/components/layout/session-provider";

// API-04のレスポンス項目名に合わせる。
export const handoverManagerSchema = z.object({
  email_address: z.string().email(),
  company_name: z.string(),
  org_id: z.string().regex(/^[A-Z0-9]{1,20}$/),
  user_name: z.string(),
  user_id: z.string().regex(/^[A-Z0-9]{1,8}$/),
});

export const handoverSearchResponseSchema = z.object({
  manager_list: z.array(handoverManagerSchema),
});

export type HandoverManager = z.infer<typeof handoverManagerSchema>;

export function canRegisterHandover(authority?: SessionAuthorityInfo): boolean {
  return (authority?.org_type_code === "01" && authority.role === "0") ||
    (authority?.org_type_code === "02" && authority.role === "9");
}

export function canTransferReportData(fromOrgId: string, toOrgId: string): boolean {
  return fromOrgId !== toOrgId && fromOrgId.startsWith("BNK") && toOrgId.startsWith("BNK");
}

export function isFutureHandoverDate(value: string, today = new Date()): boolean {
  if (!/^\d{4}\/\d{2}\/\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split("/").map(Number);
  const date = new Date(year, month - 1, day);
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  return date.getFullYear() === year && date.getMonth() === month - 1 &&
    date.getDate() === day && date > startOfToday;
}
