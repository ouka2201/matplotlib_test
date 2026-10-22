import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "~/components/ui/toaster";
import { SessionProvider } from "./session-provider";
import { MenuProvider } from "./menu-provider";
import { LoadingProvider } from "./loading-provider";
import { AuthorityProvider } from "~/hooks/useAuth";
// import { ConfirmProvider } from "./confirm-provider";

const queryClient = new QueryClient();

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MenuProvider>
        <SessionProvider>
          <LoadingProvider>
            {/* <ConfirmProvider> */}
              <Toaster />
              {children}
            {/* </ConfirmProvider> */}
          </LoadingProvider>
        </SessionProvider>
      </MenuProvider>
    </QueryClientProvider>
  );
}
