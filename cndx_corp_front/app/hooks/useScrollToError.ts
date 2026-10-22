import { useLayoutEffect, useRef } from "react";

export function useScrollToError(error: string | string[]) {
  const ref = useRef<HTMLElement | null>(null);

  useLayoutEffect(() => {
    if (!error) return;
    ref.current?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }, [error]);

  return ref;
}
