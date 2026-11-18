import { useLocation, useNavigate } from "@remix-run/react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { z } from "zod";
import ErrorHint from "~/components/common/error-hint";
import MasterLayout from "~/components/layout/master-layout";
import { useSession } from "~/components/layout/session-provider";
import { AlertModal } from "~/components/modal/alert-modal";
import { HandoverConfirmationModal } from "~/components/screen/master/mgmg05/HandoverConfirmationModal";
import { Button } from "~/components/ui/button";
import { Checkbox } from "~/components/ui/checkbox";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { API_ENDPOINTS } from "~/constants/api-endpoints";
import { HANDOVER_TYPE_INDIVIDUAL } from "~/constants/handover";
import { getData } from "~/lib/fetch";
import { canRegisterHandover } from "~/lib/validations/mgmg03";
import type { HandoverState } from "~/types/screen/master/mgmg05";

const handoverParamsSchema = z.object({
  handover_from_org_id: z.string(), handover_from_user_id: z.string(),
  handover_to_org_id: z.string(), handover_to_user_id: z.string(),
  handover_schedule_date: z.string(), report_data_flg: z.boolean(),
});
const companiesSchema = z.object({ manager_list: z.array(z.object({
  company_name: z.string(), corporate_number: z.string(), company_address: z.string(),
})) });
const scheduledSchema = z.object({ selected_company_list: z.array(z.string()) });
type Company = z.infer<typeof companiesSchema>["manager_list"][number];
type Filters = { company_name: string; corporate_number: string; company_address: string };
const emptyFilters: Filters = { company_name: "", corporate_number: "", company_address: "" };

export default function IndividualHandover() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const { session } = useSession();
  const handover = useMemo(() => {
    const parsed = handoverParamsSchema.safeParse(state);
    return parsed.success ? parsed.data : null;
  }, [state]);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [criteria, setCriteria] = useState<Filters>(emptyFilters);
  const [refresh, setRefresh] = useState(0);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [confirmInput, setConfirmInput] = useState<HandoverState | null>(null);
  const [cancelOpen, setCancelOpen] = useState(false);
  const previous = state as { fromManager?: unknown; toManager?: unknown;
    scheduleDate?: string; hasReportData?: boolean } | null;

  const load = useCallback(async (next: Filters, signal: AbortSignal) => {
    if (!handover || !session?.token) return;
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ handover_from_user_id: handover.handover_from_user_id, ...next });
      const result: unknown = await getData(
        `${API_ENDPOINTS.CONTACT_PERSON.API_INDIVIDUAL_HANDOVER_SEARCH}?${params}`,
        { Authorization: `Bearer ${session.token}` }, { signal },
      );
      const list = companiesSchema.parse(result).manager_list;
      const scheduledParams = new URLSearchParams({
        handover_to_org_id: handover.handover_to_org_id,
        handover_to_user_id: handover.handover_to_user_id,
      });
      list.forEach(({ corporate_number: corporateNumber }) => scheduledParams.append("corp_number_list", corporateNumber));
      const scheduled: unknown = await getData(
        `${API_ENDPOINTS.CONTACT_PERSON.API_SELECT_SCHEDULED_COMPANY}?${scheduledParams}`,
        { Authorization: `Bearer ${session.token}` }, { signal },
      );
      if (signal.aborted) return;
      setCompanies(list);
      setSelected((current) => [...new Set([...current, ...scheduledSchema.parse(scheduled).selected_company_list])]);
    } catch (cause) {
      if (!signal.aborted) setError(cause instanceof Error ? cause.message : "企業検索に失敗しました。");
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, [handover, session?.token]);

  useEffect(() => {
    const controller = new AbortController();
    void load(criteria, controller.signal);
    return () => controller.abort();
  }, [criteria, refresh, load]);

  const allSelected = companies.length > 0 && companies.every((company) => selected.includes(company.corporate_number));
  const toggleAll = () => setSelected((current) => allSelected
    ? current.filter((number) => !companies.some((company) => company.corporate_number === number))
    : [...new Set([...current, ...companies.map((company) => company.corporate_number)])]);
  const toggle = (number: string) => setSelected((current) => current.includes(number)
    ? current.filter((item) => item !== number) : [...current, number]);
  let screenError = "";
  if (!canRegisterHandover(session?.authorityInfo)) {
    screenError = "個別引継を利用する権限がありません。";
  } else if (!handover) {
    screenError = "引継情報がありません。営業担当引継画面から開いてください。";
  }

  return <MasterLayout isEditing={canRegisterHandover(session?.authorityInfo)} breadcrumbItems={[
    { title: "営業担当引継", link: "/master/mgmg03" }, { title: "個別引継", link: "" },
  ]}>
    {screenError ? <ErrorHint message={screenError} /> : <div className="space-y-6 pb-8">
        <h1 className="text-xl font-semibold">引継対象選択</h1>
        <form className="grid gap-4 md:grid-cols-3" onSubmit={(event) => {
          event.preventDefault(); setCriteria({ ...filters });
        }}>
          <div><Label htmlFor="company-name">お客さま名</Label><Input id="company-name" maxLength={100}
            value={filters.company_name} onChange={(event) => setFilters({ ...filters, company_name: event.target.value })} /></div>
          <div><Label htmlFor="corporate-number">法人番号</Label><Input id="corporate-number" maxLength={13}
            value={filters.corporate_number} onChange={(event) => setFilters({ ...filters, corporate_number: event.target.value })} /></div>
          <div><Label htmlFor="company-address">本社所在地</Label><Input id="company-address" maxLength={120}
            value={filters.company_address} onChange={(event) => setFilters({ ...filters, company_address: event.target.value })} /></div>
          <div className="flex gap-2 md:col-span-3">
            <Button type="submit" disabled={loading}>検索</Button>
            <Button type="button" variant="third" onClick={() => {
              setFilters(emptyFilters); setSelected([]); setCriteria({ ...emptyFilters }); setRefresh((value) => value + 1);
            }}>リセット</Button>
          </div>
        </form>
        {error && <ErrorHint message={error} />}
        <p aria-live="polite">{loading ? "検索中..." : `${companies.length}件`}</p>
        <Table><TableHeader><TableRow>
          <TableHead><Checkbox aria-label="すべて選択" checked={allSelected} onCheckedChange={toggleAll} /></TableHead>
          <TableHead>お客さま名</TableHead><TableHead>法人番号</TableHead><TableHead>本社所在地</TableHead>
        </TableRow></TableHeader><TableBody>{companies.map((company) => <TableRow key={company.corporate_number}>
          <TableCell><Checkbox aria-label={`${company.company_name}を選択`} checked={selected.includes(company.corporate_number)}
            onCheckedChange={() => toggle(company.corporate_number)} /></TableCell>
          <TableCell>{company.company_name}</TableCell><TableCell>{company.corporate_number}</TableCell>
          <TableCell>{company.company_address}</TableCell>
        </TableRow>)}</TableBody></Table>
        <div className="flex justify-between">
          <Button variant="third" onClick={() => setCancelOpen(true)}>キャンセル</Button>
          <Button disabled={selected.length === 0 || loading} onClick={() => setConfirmInput({
            handover_type: HANDOVER_TYPE_INDIVIDUAL,
            handover: { ...handover, corp_number_list: selected },
          })}>引継実施</Button>
        </div>
        {confirmInput && <HandoverConfirmationModal isOpen input={confirmInput}
          onClose={() => setConfirmInput(null)} onRegistered={() => navigate("/master/msmg01")} />}
        <AlertModal isOpen={cancelOpen} onClose={() => navigate("/master/mgmg03", { state: previous })}
          onConfirm={() => navigate("/master/msmg01")} loading={false} title="入力内容の確認"
          description="入力内容が破棄されます。よろしいですか？" cancelText="いいえ" continueText="はい" />
      </div>}
  </MasterLayout>;
}
