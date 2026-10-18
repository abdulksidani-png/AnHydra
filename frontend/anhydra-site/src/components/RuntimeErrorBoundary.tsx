import { useEffect } from "react";
import type { ErrorComponentProps } from "@tanstack/react-router";

declare global {
  interface Window {
    onRenderError?: (error: unknown) => void;
    onRenderErrorCleared?: () => void;
  }
}

export function RuntimeErrorBoundary(props: ErrorComponentProps) {
  useEffect(() => {
    window.onRenderError?.(props.error);
    return () => window.onRenderErrorCleared?.();
  }, [props.error]);

  if (typeof window !== "undefined" && typeof window.onRenderError === "function") {
    return null;
  }

  return (
    <div role="alert" style={{ padding: "4rem 1.5rem", textAlign: "center" }}>
      <h1 style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>Something went wrong</h1>
      <p>Please refresh the page, or try again in a moment.</p>
    </div>
  );
}
