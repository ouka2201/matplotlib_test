import { MetaFunction } from "@remix-run/node";
import { useCallback, useEffect, useReducer, useState } from "react";
import SearchForm from "~/components/common/search-form";
import { Messages } from "~/constants/messages/message";
import { useLoadingSpinner } from "~/hooks/use-loadingspinner";
import { postData } from "~/lib/fetch";
export const meta: MetaFunction = () => {
  return [{ title: "同意書取得組織選択" }, { name: "description", content: "search Agreement Org " }];
};

interface OrgInfo {
  org_id: string;
  org_name: string;
}

interface OrgMasterState {
  isLoading: boolean;
  searchCondition: {
    org_name: string;
    agreement_category: string;
  };
  searchResults: OrgInfo[];
}

type OrgMasterAction =
  | { type: "SET_LOADING"; payload: boolean }
  | { type: "SET_SEARCH_CONDITION"; payload: Partial<OrgMasterState["searchCondition"]> }
  | { type: "SET_SEARCH_RESULTS"; payload: OrgInfo[] };

const orgMasterReducer = (state: OrgMasterState, action: OrgMasterAction): OrgMasterState => {
  switch (action.type) {
    case "SET_LOADING":
      return { ...state, isLoading: action.payload };
    case "SET_SEARCH_CONDITION":
      return { ...state, searchCondition: { ...state.searchCondition, ...action.payload } };
    case "SET_SEARCH_RESULTS":
      return { ...state, searchResults: action.payload };
    default:
      return state;
  }
};

export default function SearchOrganization(props: {
  onSelect: (org: { id: string; name: string }) => void;
  agreementCategory: string;
}) {
  const { withLoading } = useLoadingSpinner();
  const [orgName, setOrgName] = useState("");
  const [state, dispatch] = useReducer(orgMasterReducer, {
    isLoading: false,
    searchCondition: {
      org_name: "",
      agreement_category: props.agreementCategory,
    },
    searchResults: [],
  });

  // 検索処理
  const loadItems = useCallback(async () => {
    dispatch({ type: "SET_LOADING", payload: true });
    try {
      const requestUrl = "/api/mst_manage/org/info";
      const requestParams = {
        org_name: orgName,
        agreement_category: props.agreementCategory,
      };
      const response = await withLoading(() => postData(requestUrl, requestParams));

      dispatch({ type: "SET_SEARCH_RESULTS", payload: response });
    } catch (error) {
      console.error(Messages.VALIDATION.api.search_error, error);
      dispatch({ type: "SET_SEARCH_RESULTS", payload: [] });
    } finally {
      dispatch({ type: "SET_LOADING", payload: false });
    }
  }, [orgName, props.agreementCategory, withLoading]);

  // 初期表示時に検索実行
  useEffect(() => {
    loadItems();
  }, [state.searchCondition.agreement_category]);

  return (
    <div>
      <SearchForm
        // searchConditionTitle="組織名"
        fields={[{ id: "org_name", label: "組織名", placeholder: "" }]}
        values={{ org_name: orgName }}
        onValueChange={(val) => setOrgName(val.org_name || "")}
        onSearch={loadItems}
      />

      {/* 検索結果表示エリア */}
      <div className="mt-8 border rounded-md overflow-hidden">
        <div className="max-h-96 overflow-y-auto">
          <table className="w-full caption-bottom text-sm">
            <thead className="sticky top-0 bg-background border-b">
              <tr>
                <th className="w-[10%] p-2 text-left">No</th>
                <th className="w-[90%] p-2 text-left">組織名</th>
              </tr>
            </thead>
            <tbody>
              {state.searchResults.length > 0 ? (
                state.searchResults.map((item, index) => (
                  <tr key={item.org_id} className="border-b hover:bg-muted/50 h-10">
                    <td className="w-[10%] p-2 text-left">{index + 1}</td>
                    <td className="w-[90%] p-2 text-left">
                      <button
                        onClick={() =>
                          props.onSelect({
                            id: item.org_id,
                            name: item.org_name,
                          })
                        }
                        className="text-[#00897b] underline font-semibold cursor-pointer bg-transparent border-none p-0"
                        type="button"
                      >
                        {item.org_name}
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={2} className="p-2 text-center">{Messages.SEARCH_NONE}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
