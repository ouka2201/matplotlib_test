import React from 'react';
//import EnergyDataView from "../components/energy_view_info/energy_data_view";
import ExcelSuccess from '../components/excel_success';
import main_styles from '../styles/main.module.css';
// import { MetaFunction } from '@remix-run/node';

// export const meta: MetaFunction = () => {
//   return [
//     { title: "アップロード完了" },
//     { name: "description", content: "upload Success" },
//   ];
// };

const excel_success: React.FC = () => {
  return (

    <div className={main_styles.div_class}>
      <ExcelSuccess />
    </div>
  );
};

export default excel_success;