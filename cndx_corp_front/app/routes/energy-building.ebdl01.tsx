import React from 'react';
import main_styles from '~/styles/middleBase.module.css';

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
      <h1>各種フォーマット出力画面</h1>
    </div>
  );
};

export default inputData;