import { HeadContent, Outlet, createRootRoute } from "@tanstack/react-router";
import { Layout } from "@/components/Layout";

export const Route = createRootRoute({
  component: () => (
    <>
      <HeadContent />
      <Layout>
        <Outlet />
      </Layout>
    </>
  ),
});
