import { useCallback, useEffect, useState } from "react";
import SearchForm from "~/components/common/search-form";
import { Messages } from "~/constants/messages/message";

interface DepartmentInfo {
    id: string;
    name: string;
    orgTypeCode: string;
}

export default function SearchDepartment(props: {
    departmentList: DepartmentInfo[];
    onSelect: (dept: { id: string; name: string; orgTypeCode: string }) => void;
}) {
    const [keyword, setKeyword] = useState("");
    const [filtered, setFiltered] = useState<DepartmentInfo[]>(props.departmentList);

    // 初期表示（全件）
    useEffect(() => {
        setFiltered(props.departmentList);
    }, [props.departmentList]);

    // 検索処理
    const handleSearch = useCallback(() => {
        if (!keyword.trim()) {
            setFiltered(props.departmentList);
            return;
        }

        const list = props.departmentList.filter((d) =>
            d.name.includes(keyword.trim())
        );

        setFiltered(list);
    }, [keyword, props.departmentList]);

    return (
        <div>
            {/* --- 検索フォーム --- */}
            <SearchForm
                fields={[{ id: "dept_name", label: "支店名", placeholder: "" }]}
                values={{ dept_name: keyword }}
                onValueChange={(val) => setKeyword(val.dept_name || "")}
                onSearch={handleSearch}
            />

            {/* --- 検索結果 --- */}
            <div className="mt-8 border rounded-md overflow-hidden">
                <div className="max-h-80 overflow-y-auto">
                    <table className="w-full caption-bottom text-sm">
                        <thead className="sticky top-0 bg-background border-b">
                            <tr>
                                <th className="w-[10%] p-2 text-left">No</th>
                                <th className="w-[90%] p-2 text-left">支店名</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.length > 0 ? (
                                filtered.map((item, index) => (
                                    <tr key={item.id} className="border-b hover:bg-muted/50 h-10">
                                        <td className="w-[10%] p-2">{index + 1}</td>
                                        <td className="w-[90%] p-2">
                                            <button
                                                type="button"
                                                onClick={() =>
                                                    props.onSelect({
                                                        id: item.id,
                                                        name: item.name,
                                                        orgTypeCode: item.orgTypeCode,
                                                    })
                                                }
                                                className="text-[#00897b] underline font-semibold cursor-pointer bg-transparent border-none p-0"
                                            >
                                                {item.name}
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            ) : (
                                <tr>
                                    <td colSpan={2} className="p-2 text-center">
                                        {Messages.SEARCH_NONE}
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
