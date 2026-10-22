// import React, { createContext, useContext, useEffect, useState } from 'react';

// type MasterData = {
//   M_PREFECTURE: { pref_cd: string; pref_nm: string }[];
//   // 他のマスタも必要ならここに定義
// };

// const MasterContext = createContext<MasterData | null>(null);

// export const MasterProvider = ({ children }: { children: React.ReactNode }) => {
//   const [masterData, setMasterData] = useState<MasterData>({
//     M_PREFECTURE: [],
//   });
  
//   useEffect(() => {
//     const fetchMasters = async () => {
//       try {
//         const res = await fetch('/api/master'); // API はマスタデータを返す想定
//         const data = await res.json();
//         setMasterData(data);
//         sessionStorage.setItem('m_prefecture', JSON.stringify(data.M_PREFECTURE)); // キャッシュ
//       } catch (err) {
//         console.error('マスタデータ取得エラー', err);
//       }
//     };

//     fetchMasters();
//   }, []);

//   return <MasterContext.Provider value={masterData}>{children}</MasterContext.Provider>;
// };

// export const useMasterContext = () => useContext(MasterContext);


// providers/master-provider.tsx
import { createContext, useContext, useEffect, useState } from "react";
import { useMatches } from "@remix-run/react";
import { getMasterData } from "~/utils/master-fetcher";

const MasterContext = createContext<any>(null);

export const useMaster = () => useContext(MasterContext);

export function MasterProvider({ children }: { children: React.ReactNode }) {
  const matches = useMatches();
  const currentRoute = matches[matches.length - 1]?.id;

  const [masterData, setMasterData] = useState<any>(null);

  useEffect(() => {
    if (!currentRoute) return;
    getMasterData(currentRoute).then(setMasterData);
  }, [currentRoute]);

  return (
    <MasterContext.Provider value={masterData}>
      {children}
    </MasterContext.Provider>
  );
}

