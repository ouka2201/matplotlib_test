import { ColumnDef } from "@tanstack/react-table";
import { Control, Controller } from "react-hook-form";
import { UserInfoForm, UserInfoList, UserInfoRow } from "~/types/screen/master/msus/msusType";

export const userInfoColumns = (
  selectedRows: Record<string, boolean>,
  setSelectedRows: React.Dispatch<React.SetStateAction<Record<string, boolean>>>,
  statusOptions: { value: string; label: string }[],
  userRoleOptions: { value: string; label: string }[],
  isEditing: boolean,
  control: Control<UserInfoForm>,
  loginUserId: string | null,
  isBank: boolean,
  filteredStatusOptions: { value: string; label: string }[],
  updateChangedCount: () => void,
  visibleRows: UserInfoRow[],
  allChecked?: boolean,
): ColumnDef<UserInfoList>[] => [
  ...(isEditing === false && isBank === true
    ? [] // 非表示
    : [
        {
          accessorKey: "checkbox",
          header: () => {
            return (
              <input
                type="checkbox"
                checked={allChecked}
                onChange={(e) => {
                  const checked = e.target.checked;
                  const newSelected: Record<string, boolean> = {};

                  visibleRows.forEach((row) => {
                    // チェック可能条件
                    const canCheck =
                      row.user_id !== loginUserId &&
                      // 非編集モード：ステータス0のみ
                      ((!isEditing && row.user_status === "0") ||
                        // 編集モード：ステータス5以外
                        (isEditing && row.user_status !== "5"));

                    if (canCheck) {
                      newSelected[row.user_id] = checked;
                    }
                  });

                  setSelectedRows(newSelected);
                  updateChangedCount();
                }}
              />
            );
          },

          cell: ({ row }) => {
            const id = row.original.user_id;
            const status = row.original.user_status;

            const isDisabled = id === loginUserId || (!isEditing && status !== "0") || (isEditing && status === "5");

            return (
              <input
                type="checkbox"
                checked={!!selectedRows[id]}
                disabled={isDisabled}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setSelectedRows((prev) => ({ ...prev, [id]: checked }));
                }}
              />
            );
          },

          size: 50,
          enableSorting: false,
        },
      ]),
  {
    accessorKey: "company_name",
    header: "企業名",
    enableResizing: true,
    size: 180,
    minSize: 180,
    maxSize: 180,
  },
  {
    accessorKey: "branch_name",
    header: "支店名",
    enableResizing: true,
    size: 180,
    minSize: 180,
    maxSize: 180,
  },
  // {
  //   accessorKey: "user_id",
  //   header: "ユーザーID",
  //   enableResizing: true,
  //   size: 150,
  //   minSize: 100,
  //   maxSize: 300,
  // },
  {
    accessorKey: "user_name",
    header: "氏名",
    enableResizing: true,
    size: 180,
    minSize: 180,
    maxSize: 180,
    cell: ({ row }) => {
      const index = row.index;
      const isSelected = selectedRows[row.original.user_id];
      const isDisabled = row.original.user_id === loginUserId || !isSelected;

      return isEditing ? (
        <Controller
          name={`rows.${index}.user_name`}
          control={control}
          render={({ field, fieldState }) => (
            <input
              type="text"
              {...field}
              className={`border p-1 rounded w-full ${fieldState.error ? "input-text-error" : ""}`}
              disabled={isDisabled}
              onBlur={() => {
                field.onBlur();
                updateChangedCount();
              }}
            />
          )}
        />
      ) : (
        <span>{row.original.user_name}</span>
      );
    },
  },
  {
    accessorKey: "email_address",
    header: "メールアドレス",
    enableResizing: true,
    size: 180,
    minSize: 180,
    maxSize: 180,
    cell: ({ row }) => {
      const index = row.index;
      const isSelected = selectedRows[row.original.user_id];
      const isDisabled = row.original.user_id === loginUserId || !isSelected;

      return isEditing ? (
        <Controller
          name={`rows.${index}.email_address`}
          control={control}
          render={({ field, fieldState }) => (
            <input
              type="text"
              {...field}
              className={`border p-1 rounded w-full ${fieldState.error ? "input-text-error" : ""}`}
              disabled={isDisabled}
              onBlur={() => {
                field.onBlur();
                updateChangedCount();
              }}
            />
          )}
        />
      ) : (
        <span className="whitespace-normal break-all">{row.original.email_address}</span>
      );
    },
  },
  {
    accessorKey: "user_role",
    header: "権限",
    enableResizing: true,
    size: 180,
    minSize: 180,
    maxSize: 180,
    cell: ({ row }) => {
      const index = row.index;
      const isSelected = selectedRows[row.original.user_id];
      const isDisabled = row.original.user_id === loginUserId || !isSelected;

      const originalRole = row.original.user_role;

      const roleOptionsForRow =
        originalRole === "9"
          ? userRoleOptions.filter((r) => r.value === "9")
          : userRoleOptions.filter((r) => r.value === "0" || r.value === "1");

      return isEditing ? (
        <Controller
          name={`rows.${index}.user_role`}
          control={control}
          render={({ field, fieldState }) => (
            <select
              {...field}
              className={`border p-1 rounded w-full ${fieldState.error ? "input-text-error" : ""}`}
              disabled={isDisabled}
              onBlur={() => {
                field.onBlur();
                updateChangedCount();
              }}
            >
              {/* <option value="">選択してください</option> */}
              <option value="" disabled hidden>
                選択してください
              </option>
              {roleOptionsForRow.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          )}
        />
      ) : (
        (() => {
          const code = row.original.user_role;
          const role = userRoleOptions.find((r) => r.value === code);
          return role ? role.label : "";
        })()
      );
    },
  },
  {
    accessorKey: "user_status",
    header: "ステータス",
    enableResizing: true,
    size: 180,
    minSize: 180,
    maxSize: 180,
    cell: ({ row }) => {
      const index = row.index;
      const isSelected = selectedRows[row.original.user_id];
      const isDisabled = row.original.user_id === loginUserId || !isSelected;

      return isEditing ? (
        <Controller
          name={`rows.${index}.user_status`}
          control={control}
          render={({ field, fieldState }) => {
            const currentValue = field.value ?? "";

            // プルダウンに表示する値
            const optionsForSelect = filteredStatusOptions.slice();

            // 現在値が選択肢にない場合は追加して表示
            if (currentValue && !optionsForSelect.some((s) => s.value === currentValue)) {
              const currentOption = statusOptions.find((s) => s.value === currentValue);
              if (currentOption) optionsForSelect.unshift(currentOption);
            }

            return (
              <select
                {...field}
                value={currentValue}
                className={`border p-1 rounded w-full ${fieldState.error ? "input-text-error" : ""}`}
                disabled={isDisabled}
                onBlur={() => {
                  field.onBlur();
                  updateChangedCount();
                }}
              >
                {/* <option value="">選択してください</option> */}
                <option value="" disabled hidden>
                  選択してください
                </option>
                {optionsForSelect.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            );
          }}
        />
      ) : (
        (() => {
          const code = row.original.user_status;
          const status = statusOptions.find((s) => s.value === code);
          return status ? status.label : "";
        })()
      );
    },
  },
  {
    accessorKey: "start_date",
    header: "利用開始日",
    enableResizing: true,
    size: 180,
    minSize: 180,
    maxSize: 180,
    cell: ({ row }) => {
      const value = row.getValue<string>("start_date") ?? "";
      if (value.includes("9999/12/31")) {
        return <span></span>;
      }
      const date = new Date(value);
      if (isNaN(date.getTime())) return <span></span>;

      const formatted = `${date.getFullYear()}/${(date.getMonth() + 1).toString().padStart(2, "0")}/${date
        .getDate()
        .toString()
        .padStart(2, "0")}`;
      return <span>{formatted}</span>;
    },
  },
  {
    accessorKey: "end_date",
    header: "利用終了日",
    enableResizing: true,
    size: 180,
    minSize: 180,
    maxSize: 180,
    cell: ({ row }) => {
      const value = row.getValue<string>("end_date") ?? "";
      if (value.includes("9999/12/31")) {
        return <span></span>;
      }
      const date = new Date(value);
      if (isNaN(date.getTime())) return <span></span>;

      const formatted = `${date.getFullYear()}/${(date.getMonth() + 1).toString().padStart(2, "0")}/${date
        .getDate()
        .toString()
        .padStart(2, "0")}`;
      return <span>{formatted}</span>;
    },
  },
  {
    accessorKey: "last_login_datetime",
    header: "最終ログイン日時",
    enableResizing: true,
    size: 180,
    minSize: 180,
    maxSize: 180,
    cell: ({ row }) => {
      const value = row.getValue<string>("last_login_datetime") ?? "";
      if (!value) return <span></span>;
      const date = new Date(value);
      if (isNaN(date.getTime())) return <span></span>;
      return <span>{value}</span>;
    },
  },
];

export const userInfoConfirmColumns = (
  userRoleOptions: { value: string; label: string }[],
  statusOptions: { value: string; label: string }[],
): ColumnDef<{
  user_id: string;
  user_name_before: string;
  user_name_after: string;
  email_before: string;
  email_after: string;
  role_before: string;
  role_after: string;
  status_before: string;
  status_after: string;
}>[] => [
  {
    header: "氏名",
    accessorKey: "user_name_before",
    cell: ({ row }) => <span className="whitespace-normal break-all">{row.original.user_name_after}</span>,
  },
  {
    header: "メールアドレス",
    accessorKey: "email_before",
    cell: ({ row }) => <span className="whitespace-normal break-all">{row.original.email_after}</span>,
  },
  {
    header: "権限",
    accessorKey: "role_before",
    cell: ({ row }) => {
      const roleBefore =
        userRoleOptions.find((r) => r.value === row.original.role_before)?.label ?? row.original.role_before;
      const roleAfter =
        userRoleOptions.find((r) => r.value === row.original.role_after)?.label ?? row.original.role_after;
      return <span>{roleAfter}</span>;
    },
  },
  {
    header: "ステータス",
    accessorKey: "status_before",
    cell: ({ row }) => {
      const statusBefore =
        statusOptions.find((s) => s.value === row.original.status_before)?.label ?? row.original.status_before;
      const statusAfter =
        statusOptions.find((s) => s.value === row.original.status_after)?.label ?? row.original.status_after;
      return <span>{statusAfter}</span>;
    },
  },
];

const japaneseCollator = new Intl.Collator("ja-JP");
