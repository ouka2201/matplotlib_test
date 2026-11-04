import type { z } from "zod";
import type { handoverStateSchema } from "~/lib/validations/mgmg05";

export type HandoverState = z.infer<typeof handoverStateSchema>;
export type HandoverInput = HandoverState["handover"];
