import { useLoading } from "../components/layout/loading-provider";

export const useLoadingSpinner = () => {
  const { setLoading } = useLoading();

  const withLoading = async (apiCall: () => Promise<any>) => {
    setLoading(true);
    try {
      const result = await apiCall();
      return result;
    } finally {
      setLoading(false);
    }
  };

  return { withLoading };
};
