import { useEffect, useState } from "react";
import { getMasterDataForCondition } from "~/components/layout/master-fetcher";
import { useRoleFlags } from "~/hooks/useRoleFlags";
import { getData } from "~/lib/fetch";

type ConsentRouteOption = {
  id: string;
  name: string;
};

export function useConsentRoutes(
  token: string | null,
  corporateNumber: string,
  orgId?: string
) {
  const [consentRoutes, setConsentRoutes] = useState<ConsentRouteOption[]>([]);

  const { isVis} = useRoleFlags();

  useEffect(() => {
    if (!corporateNumber) return;

    let isCancelled = false;

    const fetchConsentRoutes = async () => {
      try {
        if (!isVis) {
          const url = `/api/corp/basic-info?corporate_number=${corporateNumber}`;
          const response = await getData(url);
          if (isCancelled) return;

          const raw = Array.isArray(response.result_list)
            ? response.result_list
            : [];

          const unique = Array.from(
            new Map(
              raw.map((item: { agreement_name: string; agreement_category: string; }) => [
                item.agreement_name,
                {
                  id: item.agreement_category,
                  name: item.agreement_name,
                },
              ])
            ).values()
          ) as ConsentRouteOption[];

          setConsentRoutes(unique);
          return;
        }

        const params: Record<string, string> = { agreement_category__startswith: "1" };

        if (orgId) {
          params.org_id = orgId;
        }

        const masterEntries = [{ name: "consent-route", params }];
        const data = await getMasterDataForCondition(masterEntries, null);

        if (isCancelled) return;

        const consentRouteData = data["consent-route"] || [];
        const transformedRoutes = consentRouteData.map((item: ConsentRouteOption) => ({
          id: item.id,
          name: item.name,
        }));

        setConsentRoutes(transformedRoutes);
      } catch (err) {
        console.error("fetchConsentRoutes error:", err);
      }
    };

    fetchConsentRoutes();

    return () => {
      isCancelled = true;
    };
  }, [corporateNumber, orgId, isVis]);

  return consentRoutes;
}
