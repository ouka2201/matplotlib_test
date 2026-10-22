import React from 'react';
//import EnergyDataView from "../components/energy_view_info/energy_data_view";
import main_styles from '../styles/main.module.css';
//import Management from '../components/management';
import Management from '../pages/management';
// import { MetaFunction } from '@remix-run/node';

// export const meta: MetaFunction = () => {
//   return [
//     { title: "CNレポート作成・検索" },
//     { name: "description", content: "report management" },
//   ];
// };

const management: React.FC = () => {
  return (

    <div className={main_styles.div_class}>
      <Management />
    </div>
  );
};

export default management;