import { z } from "zod";
import { HANDOVER_TYPE_BULK, HANDOVER_TYPE_INDIVIDUAL } from "~/constants/handover";

// snake_caseのキーは呼び出し元およびAPIの入出力契約に合わせる。
export const handoverStateSchema = z.object({
  handover_type: z.enum([HANDOVER_TYPE_INDIVIDUAL, HANDOVER_TYPE_BULK]),
  handover: z.object({
    handover_from_org_id: z.string().regex(/^[0-9A-Z]{1,20}$/),
    handover_from_user_id: z.string().regex(/^[0-9A-Za-z]{1,8}$/),
    handover_to_org_id: z.string().regex(/^[0-9A-Z]{1,20}$/),
    handover_to_user_id: z.string().regex(/^[0-9A-Za-z]{1,8}$/),
    handover_schedule_date: z.string().regex(/^[0-9]{8}$/),
    report_data_flg: z.boolean(),
    corp_number_list: z.array(z.string().regex(/^[0-9]{13}$/)).optional(),
  }),
}).refine(
  (value) => value.handover_type === HANDOVER_TYPE_BULK
    || value.handover.corp_number_list !== undefined,
);
