import { createFileRoute } from "@tanstack/react-router";
import settings from "@/config/settings.json";
import { Landing } from "@/components/Landing";

export const Route = createFileRoute("/")({
  head: () => settings.routes["/"],
  component: Landing,
});
