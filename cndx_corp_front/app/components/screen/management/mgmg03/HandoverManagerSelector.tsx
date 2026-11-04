import { useEffect, useState } from "react";
import ErrorHint from "~/components/common/error-hint";
import { useSession } from "~/components/layout/session-provider";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from "~/components/ui/dialog";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "~/components/ui/table";
import { API_ENDPOINTS } from "~/constants/api-endpoints";
import { getData } from "~/lib/fetch";
import { handoverSearchResponseSchema } from "~/lib/validations/mgmg03";
import type { HandoverManager } from "~/lib/validations/mgmg03";

type HandoverManagerSelectorProps = {
  id: string;
  title: string;
  value: HandoverManager | null;
  onChange: (value: HandoverManager | null) => void;
};

export function HandoverManagerSelector({ id, title, value, onChange }: HandoverManagerSelectorProps) {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <Label htmlFor={`${id}-email`}>メールアドレス（必須）</Label>
        <div className="flex gap-2">
          <Input id={`${id}-email`} value={query} onChange={(event) => {
            setQuery(event.target.value);
            onChange(null);
          }} />
          <Dialog open={isOpen} onOpenChange={setIsOpen}>
            <DialogTrigger asChild><Button type="button" variant="third">検索</Button></DialogTrigger>
            {isOpen && <ManagerSearch initialQuery={query} onSelect={(manager) => {
              setQuery(manager.email_address);
              onChange(manager);
              setIsOpen(false);
            }} />}
          </Dialog>
        </div>
        <dl className="space-y-2">
          <div><dt>組織名</dt><dd>{value?.company_name || "未選択"}</dd></div>
          <div><dt>氏名</dt><dd>{value?.user_name || "未選択"}</dd></div>
        </dl>
      </CardContent>
    </Card>
  );
}

type SearchCriteria = { query: string; type: "email_address" | "all" };

function ManagerSearch({ initialQuery, onSelect }: {
  initialQuery: string;
  onSelect: (manager: HandoverManager) => void;
}) {
  const { session } = useSession();
  const authority = session?.authorityInfo;
  const [query, setQuery] = useState(initialQuery);
  const [searchType, setSearchType] = useState<SearchCriteria["type"]>("email_address");
  const [criteria, setCriteria] = useState<SearchCriteria | null>(
    initialQuery.trim() ? { query: initialQuery.trim(), type: "email_address" } : null,
  );
  const [managers, setManagers] = useState<HandoverManager[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (!criteria || !authority || !session?.token) return;
    let isActive = true;
    const controller = new AbortController();
    setIsLoading(true);
    setErrorMessage("");
    setManagers([]);
    const params = new URLSearchParams({
      org_id: authority.org_id, org_type_code: authority.org_type_code,
      user_role: authority.role, search_query: criteria.query, search_type: criteria.type,
    });
    void (async () => {
      try {
        const response: unknown = await getData(
          `${API_ENDPOINTS.CONTACT_PERSON.API_CONTACT_PERSON_SEARCH}?${params.toString()}`,
          { Authorization: `Bearer ${session.token}` }, { signal: controller.signal },
        );
        const parsed = handoverSearchResponseSchema.safeParse(response);
        if (!parsed.success) throw new Error("担当者検索の応答を確認できませんでした。");
        const sorted = parsed.data.manager_list.sort((a, b) =>
          a.company_name.localeCompare(b.company_name, "ja") ||
          a.user_name.localeCompare(b.user_name, "ja") ||
          a.email_address.localeCompare(b.email_address, "ja"));
        if (isActive) setManagers(sorted);
      } catch (error) {
        if (isActive) setErrorMessage(error instanceof Error ? error.message : "担当者検索に失敗しました。");
      } finally {
        if (isActive) {
          setIsLoading(false);
          setHasSearched(true);
        }
      }
    })();
    return () => { isActive = false; controller.abort(); };
  }, [criteria, authority, session?.token]);

  return (
    <DialogContent className="h-auto max-h-[80vh] w-[min(900px,95vw)] overflow-y-auto">
      <DialogTitle>営業担当の選択</DialogTitle>
      <DialogDescription>検索結果のメールアドレスを選択してください。</DialogDescription>
      <form onSubmit={(event) => {
        event.preventDefault();
        if (query.trim()) setCriteria({ query: query.trim(), type: searchType });
      }} className="space-y-3">
        <Label htmlFor="manager-query">担当者検索</Label>
        <div className="flex gap-2">
          <Input id="manager-query" value={query} onChange={(event) => setQuery(event.target.value)} />
          <Button type="submit" variant="third" disabled={!query.trim() || isLoading}>検索</Button>
        </div>
        <fieldset className="flex gap-4">
          <legend className="sr-only">検索対象</legend>
          <label><input type="radio" name="search-type" checked={searchType === "email_address"}
            onChange={() => setSearchType("email_address")} /> メールアドレス</label>
          <label><input type="radio" name="search-type" checked={searchType === "all"}
            onChange={() => setSearchType("all")} /> すべての項目</label>
        </fieldset>
      </form>
      {errorMessage && <ErrorHint message={errorMessage} />}
      <div aria-live="polite">
        {isLoading && "検索中..."}
        {!isLoading && hasSearched && !errorMessage && managers.length === 0 &&
          "該当するデータが見つかりません。"}
      </div>
      <Table>
        <TableHeader><TableRow>
          <TableHead>メールアドレス</TableHead><TableHead>組織名</TableHead><TableHead>氏名</TableHead>
        </TableRow></TableHeader>
        <TableBody>{managers.map((manager) => (
          <TableRow key={`${manager.org_id}:${manager.user_id}`}>
            <TableCell><Button type="button" variant="link" className="h-auto w-auto whitespace-normal break-all text-left" onClick={() => onSelect(manager)}>
              {manager.email_address}
            </Button></TableCell>
            <TableCell>{manager.company_name}</TableCell><TableCell>{manager.user_name}</TableCell>
          </TableRow>
        ))}</TableBody>
      </Table>
    </DialogContent>
  );
}
