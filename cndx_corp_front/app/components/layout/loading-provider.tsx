import React, { createContext, ReactNode, useState, useContext } from "react";
import {LoadingSpinner} from "~/components/common/loadingSpinner"; // 既存のローディングスピナー

type LoadingContextType = {
  isLoading: boolean;
  setLoading: (loading: boolean) => void;
};

const LoadingContext = createContext<LoadingContextType | undefined>(undefined);

export const LoadingProvider = ({ children }: { children: ReactNode }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [startTime, setStartTime] = useState<number | null>(null);
  const MIN_LOADING_TIME = 2000; // 2秒

  const setLoading = (loading: boolean) => {
    if (loading) {
      setStartTime(Date.now());
      setIsLoading(true);
    } else {
      if (startTime) {
        const elapsed = Date.now() - startTime;
        const delay = Math.max(MIN_LOADING_TIME - elapsed, 0);

        setTimeout(() => {
          setIsLoading(false);
          setStartTime(null);
        }, delay);
      } else {
        setIsLoading(false);
      }
    }
  };

  return (
    <LoadingContext.Provider value={{ isLoading, setLoading }}>
      {children}
      {isLoading && <LoadingSpinner />}
    </LoadingContext.Provider>
  );
};

// LoadingContextを使用するカスタムフック
export const useLoading = () => {
  const context = useContext(LoadingContext);
  if (!context) {
    throw new Error("useLoading must be used within a LoadingProvider");
  }
  return context;
};
