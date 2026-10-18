import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider, createRouter } from "@tanstack/react-router";
import { RuntimeErrorBoundary } from "@/components/RuntimeErrorBoundary";
import { routeTree } from "./routeTree.gen";
import "./styles.css";

const router = createRouter({
  routeTree,
  scrollRestoration: true,
  defaultErrorComponent: RuntimeErrorBoundary,
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
