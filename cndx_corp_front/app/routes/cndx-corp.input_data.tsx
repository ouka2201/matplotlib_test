import React from 'react';
// import EnergyDataView from "../components/energy_view_info/energy_data_view";
import InputDisplay from '../components/input_data';
import main_styles from '../styles/main.module.css';
//import ExcelUpload from '../pages/excelUpload';

// import { MetaFunction } from '@remix-run/node';

// export const meta: MetaFunction = () => {
//   return [
//     { title: "建物・エネルギー照会" },
//     { name: "description", content: "input data" },
//   ];
// };

const inputData: React.FC = () => {
  return (
    <div className={main_styles.div_class}>
      <InputDisplay />
    </div>
  );
};

export default inputData;