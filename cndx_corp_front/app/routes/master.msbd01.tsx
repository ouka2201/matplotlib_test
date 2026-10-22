import React from "react";
import { useLocation } from "react-router-dom";
import BuildingList from "~/components/buildingList";
import { BreadCrumbType } from "~/components/common/breadcrumb";
import MasterLayout from '~/components/layout/master-layout';

const BuildingManagement: React.FC = () => {
  const location = useLocation();
  // const navigate = useNavigate();


  const customerData = location.state?.customerData;


  const breadcrumbItems: BreadCrumbType[] = [
    { title: "お客さまマスタ登録・管理", link: "/master/mscs01" },
    {
      title: customerData?.company_name || "企業",
      link: "/master/mscs03",
      state: { customerData },
    },
    {
      title: "拠点マスタ管理",
      link: "",
    },
  ];

  return (
    <MasterLayout breadcrumbItems={breadcrumbItems}>

      <BuildingList customerData={customerData} />
    </MasterLayout>
  );
};

export default BuildingManagement;
