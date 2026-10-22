import {
  ColumnDef
} from "@tanstack/react-table";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import SearchForm from "~/components/common/search-form";
import MasterLayout from '~/components/layout/master-layout';
import { Button } from "~/components/ui/button";
import { Command, CommandList } from "~/components/ui/command";
import { PageableTable } from "~/components/ui/pageable-table";
import { Icon, Text } from "../components/import";
import { getData } from "../lib/fetch";

interface OrgCompany {
  org_id: string;
  org_name: string;
  org_type_code: string | null;
  org_type: string | null;
}

const OrganizationList: React.FC = () => {
  const navigate = useNavigate();

  const [searchResults, setSearchResults] = useState<OrgCompany[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | string[]>("");
  // 読み込み中フラグ
  const [isLoading, setIsLoading] = useState(false);
  // ▼検索条件（追加）
  const [searchCondition, setSearchCondition] = useState({
    org_name: "",
    org_type_code: "",
    org_id: "",
  });
  const [orgTypeOptions, setOrgTypeOptions] = useState<{ value: string; label: string }[]>([]);

  const updateSearchCondition = (updates: Partial<typeof searchCondition>) => {
    setSearchCondition((prev) => ({ ...prev, ...updates }));
  };

  const buildQuery = (params: Record<string, string>) => {
    const cleaned: Record<string, string> = {};
    Object.entries(params).forEach(([k, v]) => {
      if (v && v.trim() !== "") cleaned[k] = v.trim();
    });
    return new URLSearchParams(cleaned).toString();
  };

  const searchFields = useMemo(
    () => [
      {
        id: "org_name",
        label: "組織名",
        type: "text",
        placeholder: "xx株式会社",
      },
      {
        id: "org_type_code",
        label: "組織種別",
        type: "select",
        options: orgTypeOptions,
      },
      {
        id: "org_id",
        label: "組織ID",
        type: "text",
        placeholder: "xx…",
      },
    ],
    [orgTypeOptions]
  );

  // 検索API（全件/条件検索どちらもこれで対応）
  const handleSearch = useCallback(async (overrides?: Partial<typeof searchCondition>) => {
    const effective = { ...searchCondition, ...(overrides ?? {}) };

    type AuthResponse = {
      auth_list: OrgCompany[];
    };
    setIsLoading(true);
    try {
      const base = `/api/user/mst_organization/corprations/auth`;
      const query = buildQuery(effective as Record<string, string>);
      const url = query ? `${base}?${query}` : base;
      const raw = await getData(url);
      const data = raw as AuthResponse;

      if (!data.auth_list || data.auth_list.length === 0) {
        setSearchResults([]);
        return;
      }
      if (orgTypeOptions.length === 0) {
        const map = new Map<string, string>();

        data.auth_list.forEach((org) => {
          if (org.org_type_code && org.org_type) {
            map.set(org.org_type_code, org.org_type);
          }
        });

        setOrgTypeOptions(
          Array.from(map.entries())
            .sort(([, val1], [, val2]) => val1.localeCompare(val2))
            .map(([value, label]) => ({
              value,
              label,
            }))
        );
      }

      const sortedResults = data.auth_list.sort((a, b) =>
        (a?.org_name ?? "").localeCompare(b?.org_name ?? "")
      );

      setSearchResults(sortedResults);
    } catch (error: any) {
      setErrorMessage(error.data?.message);
    } finally {
      setIsLoading(false);
    }
  }, [searchCondition]);

  useEffect(() => {
    handleSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleReset = () => {
    const cleared = { org_name: "", org_type_code: "", org_id: "" };
    setSearchCondition(cleared);
    handleSearch(cleared);
  };

  // 行クリック
  const handleCustomerNameClick = (company: OrgCompany) => {
    navigate(`/master/msog04`, {
      state: { customerData: company },
    });
  };


  // カラム定義
  const columns: ColumnDef<OrgCompany>[] = [
    {
      accessorKey: "org_name",
      header: "組織名",
      cell: ({ row }) => {
        const org = row.original;

        return (
          <span
            role="button"
            tabIndex={0}
            onClick={() => handleCustomerNameClick(org)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                handleCustomerNameClick(org);
              }
            }}
            className="textlink"
          >
            {org.org_name}
          </span>
        );
      }
    },
    {
      accessorKey: "org_type",
      header: "組織種別",
      cell: ({ row }) => row.getValue("org_type") || "-"
    },
    {
      accessorKey: "org_id",
      header: "組織ID",
      cell: ({ row }) => row.getValue("org_id") || "-"
    }
  ];

  const breadcrumbItems = [
    { title: "利用組織マスタ登録・管理", link: "" }
  ];

  return (
    <MasterLayout
      isEditing={false}
      breadcrumbItems={breadcrumbItems}
    >

      <div className="space-y-6 mb-10">
        {/* エラーメッセージ */}
        {errorMessage && (
          <div className="flex flex-col border border-red-500 rounded w-4/5 overflow-hidden">
            <div className="flex flex-row items-center bg-red-500 px-4 py-2 gap-1">
              <Icon name="error-pink" />
              <Text content="エラーがあります" color="white" weight="bold" />
            </div>

            <div className="flex flex-col items-start bg-[#fee4e2] border border-[#d92d20] px-4 py-6 rounded-b text-[#d92d20] cursor-pointer gap-[25px]">
              {Array.isArray(errorMessage) ? (
                <ul>
                  {errorMessage.map((message, index) => (
                    <li key={index}>{message}</li>
                  ))}
                </ul>
              ) : (
                <div className="text-[#d92d20] text-[14px]">
                  {errorMessage}
                </div>
              )}
            </div>
          </div>
        )}

        {/* 新規登録ボタン */}
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button
              variant="primary"
              size="default"
              className="gap-1"
              onClick={() => navigate("/master/msog02")}
            >
              {/* <PlusIcon className="h-5 w-5" /> */}
              <span>新規登録</span>
            </Button>
          </div>
          {/* ▼検索条件（追加） */}
          <SearchForm
            fields={searchFields}
            values={searchCondition}
            onValueChange={updateSearchCondition}
            onSearch={() => handleSearch()}
            onReset={handleReset}
          />
        </div>
      </div>

      {/* 対象組織の選択 */}
      <Command>
        <CommandList>
          {isLoading ? (
            <div className="p-4 flex justify-center items-center text-gray-500 text-sm">
              <div className="w-5 h-5 border-2 border-gray-300 border-t-gray-500 rounded-full animate-spin mr-2"></div>
              読み込み中...
            </div>
          ) : (
            // <div className="w-full pt-4">
            <PageableTable<OrgCompany, unknown>
              columns={columns}
              data={searchResults}
              totalCount={searchResults.length}
              pageCount={Math.ceil(searchResults.length / 10)}
              pageSizeOptions={[5, 10, 20, 50]}
            />
            // </div>
          )}
        </CommandList>
      </Command>
    </MasterLayout>
  );
};

export default OrganizationList;
