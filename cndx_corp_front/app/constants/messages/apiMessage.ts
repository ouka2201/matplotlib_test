// app/constants/message.ts

export const ApiMessages = {
    
    // バリデーション（関数形式で項目名を可変に）
    common: {
      INFO:{
        INSERT_INFO: (field: string) => `${field}の登録が完了しました。`,
        UPDATE_INFO: (field: string) => `${field}の更新が完了しました。`,
        DELETE_INFO: (field: string) => `${field}の削除が完了しました。`,
      },
      ERROR: {
        NO_RESULT: (field: string) => `該当する${field}が見つかりません。`,
      }
    },
  } as const;
  