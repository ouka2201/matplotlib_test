
import React from 'react';
import confirmDialog_styles from '../../styles/confirmDialog.module.css';

interface ConfirmDialogProps {
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * ポップアップ画面、共通コンポーネントとして設定可能
 * 
 * @type {{ message: string, onConfirm: void, onCancel: void }}
 */
const ConfirmDialog: React.FC<ConfirmDialogProps> = ({ message, onConfirm, onCancel }) => {
  return (
    <div className={confirmDialog_styles.dialog_overlay}>
      <div className={confirmDialog_styles.dialog_box}>
        <p>{message}</p>
        <div className={confirmDialog_styles.dialog_buttons}>
          {/* 
          複数のスタイルの入れ子
          <button className={`${confirmDialog_styles.button} ${confirmDialog_styles.button_container}`} onClick={onConfirm}>
          */}
          <button className={confirmDialog_styles.button} onClick={onConfirm}>
            確認
          </button>
          <button className={confirmDialog_styles.button}  onClick={onCancel}>
            キャンセル
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmDialog;
