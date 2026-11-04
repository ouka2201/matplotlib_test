import { useNavigate } from "@remix-run/react";
import { useState } from "react";
import ErrorHint from "~/components/common/error-hint";
import MasterLayout from "~/components/layout/master-layout";
import { useSession } from "~/components/layout/session-provider";
import { AlertModal } from "~/components/modal/alert-modal";
import { HandoverManagerSelector } from "~/components/screen/management/mgmg03/HandoverManagerSelector";
import { HandoverConfirmationModal } from "~/components/screen/management/mgmg05/HandoverConfirmationModal";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "~/components/ui/card";
import { Checkbox } from "~/components/ui/checkbox";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { HANDOVER_TYPE_BULK } from "~/constants/handover";
import { canRegisterHandover, canTransferReportData, isFutureHandoverDate } from "~/lib/validations/mgmg03";
import type { HandoverManager } from "~/lib/validations/mgmg03";
import type { HandoverState } from "~/types/screen/management/mgmg05";

// shortcut: 仮画面は一括引継のみ。個別引継は企業選択画面の実装時に追加する。
export default function SalesHandover() {
  const navigate = useNavigate();
  const { session } = useSession();
  const [fromManager, setFromManager] = useState<HandoverManager | null>(null);
  const [toManager, setToManager] = useState<HandoverManager | null>(null);
  const [scheduleDate, setScheduleDate] = useState("");
  const [hasReportData, setHasReportData] = useState(false);
  const [confirmationInput, setConfirmationInput] = useState<HandoverState | null>(null);
  const [isCancelOpen, setIsCancelOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const canTransferReports = canTransferReportData(fromManager?.org_id ?? "", toManager?.org_id ?? "");
  const canConfirm = Boolean(fromManager && toManager && scheduleDate.trim());

  const handleConfirm = () => {
    if (!fromManager || !toManager) return;
    if (fromManager.user_id === toManager.user_id && fromManager.org_id === toManager.org_id) {
      setErrorMessage("引継元と引継先には異なる担当者を選択してください。");
      return;
    }
    if (!isFutureHandoverDate(scheduleDate)) {
      setErrorMessage("実施日はYYYY/MM/DD形式で、明日以降の有効な日付を入力してください。");
      return;
    }
    setErrorMessage("");
    setConfirmationInput({
      handover_type: HANDOVER_TYPE_BULK,
      handover: {
        handover_from_org_id: fromManager.org_id, handover_from_user_id: fromManager.user_id,
        handover_to_org_id: toManager.org_id, handover_to_user_id: toManager.user_id,
        handover_schedule_date: scheduleDate.replaceAll("/", ""),
        report_data_flg: canTransferReports && hasReportData,
      },
    });
  };

  return (
    <MasterLayout isEditing={canRegisterHandover(session?.authorityInfo)} breadcrumbItems={[
      { title: "営業担当登録・管理", link: "/master/msmg01" },
      { title: "営業担当引継", link: "" },
    ]}>
      {!canRegisterHandover(session?.authorityInfo) ? <ErrorHint message="営業担当引継を利用する権限がありません。" /> : (
        <div className="space-y-6 pb-8">
          <p>一括引継の仮画面です。担当者を検索・選択して、引継内容を入力してください。</p>
          {errorMessage && <ErrorHint message={errorMessage} />}
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-6">
              <HandoverManagerSelector id="handover-from" title="営業担当（引き継ぎ前）"
                value={fromManager} onChange={(value) => { setFromManager(value); setHasReportData(false); }} />
              <HandoverManagerSelector id="handover-to" title="営業担当（引き継ぎ後）"
                value={toManager} onChange={(value) => { setToManager(value); setHasReportData(false); }} />
            </div>
            <Card>
              <CardHeader><CardTitle>引継の詳細</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <Label htmlFor="handover-date">実施日（必須）</Label>
                <Input id="handover-date" placeholder="YYYY/MM/DD" maxLength={10}
                  value={scheduleDate} onChange={(event) => setScheduleDate(event.target.value)} />
                <div className="flex items-center gap-2">
                  <Checkbox id="handover-reports" disabled={!canTransferReports}
                    checked={canTransferReports && hasReportData}
                    onCheckedChange={(checked) => setHasReportData(checked === true)} />
                  <Label htmlFor="handover-reports">拠点・エネルギーデータ、レポートも引き継ぐ</Label>
                </div>
              </CardContent>
            </Card>
          </div>
          <div className="flex justify-between gap-4">
            <Button variant="third" onClick={() => setIsCancelOpen(true)}>キャンセル</Button>
            <Button variant="primary" disabled={!canConfirm} onClick={handleConfirm}>一括引継</Button>
          </div>
          {confirmationInput && <HandoverConfirmationModal isOpen input={confirmationInput}
            onClose={() => setConfirmationInput(null)} onRegistered={() => navigate("/master/msmg01")} />}
          <AlertModal isOpen={isCancelOpen} onClose={() => setIsCancelOpen(false)}
            onConfirm={() => navigate("/master/msmg01")} loading={false} title="入力内容の確認"
            description="入力内容が破棄されます。よろしいですか？" cancelText="いいえ" continueText="はい" />
        </div>
      )}
    </MasterLayout>
  );
}
