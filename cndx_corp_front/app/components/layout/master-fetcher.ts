import { getData, postData } from "~/lib/fetch";

// ルートごとに必要な master データとパラメータ
type MasterRequest = string | { name: string; params?: Record<string, string> };

const routeMasterMap: Record<string, MasterRequest[]> = {
  "master/mscs02": ["aggreement", { name: "prefecture", params: { includeCity: "true" } }],
  // "master/mscs03": ["consent-route", "prefecture"],
  "master/mscs03": [
    { name: "consent-route", params: { agreement_category__startswith: "0", agreement_category__ne: "00" } },
    { name: "prefecture", params: {} },
  ],
  "master/msog02": [{ name: "mcode", params: { group: "X1" } }],
  "master/msus01": [
    { name: "company_name", params: {} },
    { name: "user_status", params: {} },
    { name: "user_role", params: {} },
  ],
  "master/msus02": [
  { name: "company_name", params: {} },
  { name: "user_role", params: {} }
],

};

async function fetchMaster(name: string, token: string | null, params?: Record<string, string>) {
  const query = params ? `?${new URLSearchParams(params).toString()}` : "";
  const { res } = await getData(`/api/ui/option/${name}${query}`, {
    Authorization: `Bearer ${token}`,
  });
  return res;
}

export async function getMasterData(routeId: string, token: string) {
  const masterEntries = routeMasterMap[routeId] || [];

  const results = await Promise.all(
    masterEntries.map(async (entry) => {
      if (typeof entry === "string") {
        return [entry, await fetchMaster(entry, token)];
      } else {
        return [entry.name, await fetchMaster(entry.name, token, entry.params)];
      }
    })
  );

  return Object.fromEntries(results);
}

export async function getMasterDataForCondition(masterEntries: MasterRequest[], token: string | null) {
  const results = await Promise.all(
    masterEntries.map(async (entry) => {
      if (typeof entry === "string") {
        return [entry, await fetchMaster(entry, token)];
      } else {
        return [entry.name, await fetchMaster(entry.name, token, entry.params)];
      }
    })
  );

  return Object.fromEntries(results);
}

async function fetchMasterUser(name: string, token: string, params?: Record<string, string>) {
  const body = params ?? {};

  const res = await postData(`/api/mst_user/search/${name}`, body, {
    Authorization: `Bearer ${token}`,
  });

  return res;
}

export async function postMasterUsrData(routeId: string, token: string) {
  const masterEntries = routeMasterMap[routeId] || [];

  const results = await Promise.all(
    masterEntries.map(async (entry) => {
      if (typeof entry === "string") {
        return [entry, await fetchMasterUser(entry, token)];
      } else {
        return [entry.name, await fetchMasterUser(entry.name, token, entry.params)];
      }
    })
  );

  return Object.fromEntries(results);
}

export async function postMasterUserDataForCondition(masterEntries: MasterRequest[], token: string) {
  const results = await Promise.all(
    masterEntries.map(async (entry) => {
      if (typeof entry === "string") {
        return [entry, await fetchMasterUser(entry, token)];
      } else {
        return [entry.name, await fetchMasterUser(entry.name, token, entry.params)];
      }
    })
  );

  return Object.fromEntries(results);
}
