import { useEffect, useState } from "react";

export interface RoleFlags {
  isEpAdmin: boolean;  // EP管理者フラグ
  isEpGeneral: boolean;// EP一般ユーザーフラグ
  isBank: boolean;// 銀行ユーザーフラグ
  isBranchAdmin: boolean;// 支店管理者フラグ
  isBranchGeneral: boolean;// 支店一般ユーザーフラグ
  isRepAdmin: boolean;// REP管理者フラグ
  isRepGeneral: boolean;// REP一般ユーザーフラグ
  isTcsAdmin: boolean;// TCS管理者フラグ
  isTcsGeneral: boolean;// TCS一般ユーザーフラグ
  isJfs: boolean;// JFSユーザーフラグ
  isZrb: boolean;// ZRBユーザーフラグ
  isAse: boolean;// ASEユーザーフラグ
  isVis: boolean; // 可視化事業者フラグ
  isBankUser: boolean; // 地銀ユーザーフラグ
  isEp: boolean; // EPユーザーフラグ
  isRep: boolean; // REPユーザーフラグ
  isTcs: boolean; // TCSユーザーフラグ
}

export function useRoleFlags(): RoleFlags {
  const [flags, setFlags] = useState<RoleFlags>({
    isEpAdmin: false,
    isEpGeneral: false,
    isBank: false,
    isBranchAdmin: false,
    isBranchGeneral: false,
    isRepAdmin: false,
    isRepGeneral: false,
    isTcsAdmin: false,
    isTcsGeneral: false,
    isJfs: false,
    isZrb: false,
    isAse: false,
    isVis: false, // 可視化事業者フラグ
    isBankUser: false, // 地銀ユーザーフラグ
    isEp: false, // EPユーザーフラグ
    isRep: false, // REPユーザーフラグ
    isTcs: false, // TCSユーザーフラグ
  });

  useEffect(() => {
    if (typeof window === "undefined") return; // SSR対策

    const stored = JSON.parse(sessionStorage.getItem("userRoleFlags") || "{}");
    const {
      isBank = false,
      isBranchAdmin = false,
      isBranchGeneral = false,
      isJfs = false,
      isAse = false,
      isZrb = false,
      isEpAdmin = false,
      isEpGeneral = false,
      isRepAdmin = false,  
      isRepGeneral = false,
      isTcsAdmin = false,
      isTcsGeneral = false,
    } = stored;

    setFlags({
      isEpAdmin: isEpAdmin,
      isEpGeneral: isEpGeneral,
      isBank: isBank,
      isBranchAdmin: isBranchAdmin,
      isBranchGeneral: isBranchGeneral,
      isRepAdmin: isRepAdmin,
      isRepGeneral: isRepGeneral,
      isTcsAdmin: isTcsAdmin,
      isTcsGeneral: isTcsGeneral,
      isJfs: isJfs,
      isZrb: isZrb,
      isAse: isAse,
      isVis: isJfs || isAse || isZrb,
      isBankUser: isBank || isBranchAdmin || isBranchGeneral,
      isEp: isEpAdmin || isEpGeneral,
      isRep: isRepAdmin || isRepGeneral,
      isTcs: isTcsAdmin || isTcsGeneral,  
    });
  }, []);

  return flags;
}
